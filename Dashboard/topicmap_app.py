# ========== (c) JP Hwang 2020-04-02  ==========

import logging

# ===== START LOGGER =====
logger = logging.getLogger(__name__)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
sh = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
sh.setFormatter(formatter)
root_logger.addHandler(sh)

import pandas as pd
import numpy as np
import plotly.express as px
import dash
import dash_cytoscape as cyto
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash.dependencies import Input, Output
#from .Dash_fun import apply_layout_with_auth, load_object, save_object
#from sklearn.manifold import TSNE
#import umap  # pip install umap-learn
import json

import sys
import os
from pathlib import Path
import pandas as pd
from itertools import cycle

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = PARENT_DIR + '/data'
PREPO_DIR = PARENT_DIR + '/prepo'

sys.path.insert(0, PARENT_DIR)
sys.path.insert(0, PREPO_DIR)
from prepo.topic_model import TopicModel 
from prepo import utils

url_base = '/dash/app6/'
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server


# docs 데이터 불러오기. #### 이 부분 db에서 불러오도록 수정필요 #####
tm_model_path = DATA_DIR + '/tm_model.z'
user_docs_df = utils.load_obj(DATA_DIR + '/', 'user_docs_df.pkl')  
user_docs_df = user_docs_df.reset_index(level=0).rename(columns={"index":"id", 'contents_prep_sum': 'text_sum'})

# 모델 불러오기 또는 로드하기
BUILD_TM_MODEL = False
if BUILD_TM_MODEL or not Path(tm_model_path).exists():
    tm_model = TopicModel(user_docs_df['contents_prep_sum'], 
                    doc_ids=user_docs_df['id'],
                    )
    tm_model.save(tm_model_path)
    print("tm_model is saved")
else:
    tm_model = TopicModel.load(tm_model_path)
    print("tm_model is loaded")


# docs 데이터 + top2vec모델 데이터 결합하여 사용할 df 만들기
topics_idx_vector, docs_idx_vector, words_idx_vector = tm_model.get_2d_vectors()  # id, x, y 리턴

topic_df = pd.DataFrame(topics_idx_vector)
topic_df['topic_idx'] = topic_df['id']
docs_idx_vector_df = pd.DataFrame(docs_idx_vector)
word_df = pd.DataFrame(words_idx_vector)
word_df['topic_idx'] = -1

# topics_idx_vector_df['element_type'] ='topic'
# topics_idx_vector_df['topic_idx'] = topics_idx_vector_df['id']
# docs_idx_vector_df['element_type'] = 'doc'
# words_idx_vector_df['element_type'] = 'word'
# words_idx_vector_df['topic_idx'] = -1

#network_df = pd.concat([topics_idx_vector_df,docs_idx_vector_df, words_idx_vector_df])
#user_docs_df['element_type'] = 'doc'
doc_df = pd.merge(docs_idx_vector_df, user_docs_df, on=['id'], how = 'left')
#print(network_df.head())
# print(network_df.isnull().sum())
# print(network_df.columns)
# print(network_df['element_type'].value_counts())
# print(network_df.loc[network_df['element_type'] == 'doc', :][:2])
# print(network_df["topic_idx"].unique())


############### network_df에서 'element_type'가 doc인것에 대해  ['title', 'publish_date', 'text_sum', 'url'] 추가해주세요#########
# from_doc_db_colname = ['title', 'publish_date', 'text_sum', 'url']
# for colname in from_doc_db_colname:
#     network_df[colname] = colname+'22'

#doc_info_colnames = ['title', 'publish_date', 'contents', 'url', 'crawl_at', 'is_news', 'clip_at', 'contents_prep', 'text_sum', ]  #  'cited_by', 'n_cites', 
vector_colnames = ['x','y'] # id, topic_idx, word
#position_arr = network_df.loc[:, vector_colnames].to_numpy()

# position_arr = {"topic": 50, 
#                     "doc": 20, 
#                     "word": 10}

# Prep data / fill NAs
# for colname in doc_info_colnames:
#     network_df[colname] = network_df[colname].fillna("")
#network_df["cited_by"] = network_df["cited_by"].fillna("")   # edge하려면 이거 수정해줘야함
##network_df["topic_idx"] = network_df["topic_idx"].astype(str)
# topic_idxs = [str(i) for i in range(len(network_df["topic_idx"].unique()))]
# lda_val_arr = network_df[topic_idxs].values


with open("/home/lab13/prepo-flask-gentelella/data/lda_topics.json", "r") as f:
    lda_topics = json.load(f)
topics_txt = [lda_topics[str(i)] for i in range(len(lda_topics))]
topics_txt = [[j.split("*")[1].replace('"', "") for j in i] for i in topics_txt]

topics_txt = ["; ".join(i) for i in topics_txt]
print(topics_txt)
#element_type_ser = network_df.groupby("element_type")["topic_idx"].count().sort_values(ascending=False)
element_type_ser = {"topic": len(topic_df), 
                    "doc": len(doc_df),
                    "word": len(word_df),}

def tsne_to_cyto(tsne_val, scale_factor=40):
    return int(scale_factor * (float(tsne_val)))


def get_node_list(topic_df, doc_df, word_df):  # Convert DF data to node list for cytoscape
    node_list = []
    # topic
    node_list += [{
            "data": {
                "id": row["id"], #str(idx),
                "element_type": "topic",
            },
            "position": {"x": tsne_to_cyto(row["x"]), "y": tsne_to_cyto(row["y"])},
            "classes": row["topic_idx"],
            "selectable": True,
            "grabbable": False,
        } for idx, row in topic_df.iterrows()] 

    # doc
    node_list += [{
            "data": {
                "id": row["id"],  # 원 db의 아이디. 물론 docs만 의미있...
                "title": row["title"],
                "element_type": "doc",
                "publish_date": row["publish_date"],
                "text_sum": row["text_sum"],
                #"cited_by": row["cited_by"],
                #"n_cites": row["n_cites"],
                "node_size": node_size_dict[row["element_type"]], #int(np.sqrt(1 + row["n_cites"]) * 10),
                "url": row["url"],
            },
            "position": {"x": tsne_to_cyto(row["x"]), "y": tsne_to_cyto(row["y"])},
            "classes": row["topic_idx"],
            "selectable": True,
            "grabbable": False,
        }
        for idx, row in doc_df.iterrows()
    ]
    # word
    node_list += [
        {
            "data": {
                "id": row["id"],  # 원 db의 아이디. 물론 docs만 의미있...
                "element_type": "word",
                "label": row['word']
            },
            "position": {"x": tsne_to_cyto(row["x"]), "y": tsne_to_cyto(row["y"])},
            "classes": row["topic_idx"],
            "selectable": True,
            "grabbable": False,
        }
        for idx, row in word_df.iterrows()
    ]

    return node_list


default_tsne = 40

def update_node_data(dim_red_algo, tsne_perp, topic_df, doc_df, word_df, position_arr):
    #(x_list, y_list) = get_node_locs(vectors_df, dim_red_algo, tsne_perp=tsne_perp)
    x_list = position_arr[:, 0]
    y_list = position_arr[:, 1]

    x_range = max(x_list) - min(x_list)
    y_range = max(y_list) - min(y_list)
    # print("Ranges: ", x_range, y_range)

    scale_factor = int(4000 / (x_range + y_range))
    in_df["x"] = x_list
    in_df["y"] = y_list

    tmp_node_list = get_node_list(topic_df, doc_df, word_df)
    for i in range(
        len(in_df)
    ):  # Re-scaling to ensure proper canvas scaling vs node sizes 
        tmp_node_list[i]["position"]["x"] = tsne_to_cyto(x_list[i], scale_factor)
        tmp_node_list[i]["position"]["y"] = tsne_to_cyto(y_list[i], scale_factor)

    return tmp_node_list


startup_n_cites = 1  #startup_elms["n_cites"]
startup_element_types = ["topic", "doc", "word"]
startup_elm_list = []


col_swatch = cycle(px.colors.qualitative.Plotly) #px.colors.qualitative.Dark24
def_stylesheet = [ ]
for topic_idx in topic_df["topic_idx"].unique():
    color = next(col_swatch)
    def_stylesheet.append({
        "selector": "." + str(topic_idx),  # word는 -1이기 때문
        "style": {"background-color": color, "line-color": color},
    })


def_stylesheet += [
    {
        "selector": "node",
        "style": {}
        #"style": {"width": "data(node_size)", "height": "data(node_size)"},
    },
    #{"selector": "edge", "style": {"width": 1, "curve-style": "bezier"}},
]
# type
def_stylesheet += [
    {
        "selector": '[element_type = "topic"]',
        "style": {"width": 30, "height": 30,
                    'shape': 'star'},
    },
    {
        "selector": '[element_type = "doc"]',
        "style": {"width": 10, "height": 10,
                    'shape': 'ellipse'},
    },
    {
        "selector": '[element_type = "word"]',
        "style": {"width": 1, "height": 1,
                    #'shape': 'ellipse',
                    'content': 'data(label)'},
    },
]


topics_html = list()
for topic_html in [
    html.Span([str(i) + ": " + topics_txt[i]], style={"color": next(col_swatch)})
    for i in range(len(topics_txt))
]:
    topics_html.append(topic_html)
    topics_html.append(html.Br())

body_layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        dcc.Markdown(
                            """
                -----
                ##### Topics:
                -----
                """
                        ),
                        html.Div(
                            topics_html,
                            style={
                                "fontSize": 11,
                                "height": "100px",
                                "overflow": "auto",
                            },
                        ),
                    ],
                    sm=12,
                    md=8,
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Row(
                            [
                                cyto.Cytoscape(
                                    id="core_19_cytoscape",
                                    layout={"name": "preset"},
                                    style={"width": "100%", "height": "600px"},
                                    elements=startup_elm_list,
                                    stylesheet=def_stylesheet,
                                    minZoom=0.06,
                                )
                            ]
                        ),
                        dbc.Row(
                            [
                                dbc.Alert(
                                    id="node-data",
                                    children="Click on a node to see its details here",
                                    color="secondary",
                                )
                            ]
                        ),
                    ],
                    sm=12,
                    md=8,
                ),
                dbc.Col(
                    [
                        dbc.Badge(
                            "element_type:", color="info", className="mr-1"
                        ),
                        dbc.FormGroup(
                            [
                                dcc.Checklist(
                                    id="element_types_dropdown",
                                    options=[
                                        {
                                            "label": k+ " ("+ str(v)+ ")",
                                            "value": k,
                                        }
                                        for k, v in element_type_ser.items()
                                    ],
                                    value=startup_element_types,
                                    #multi=True,
                                    style={"width": "100%"},
                                ),
                            ]
                        ),
                    ],
                    sm=12,
                    md=4,
                ),
            ]
        ),
        dbc.Row(
            [
                dcc.Markdown(" "
            #         """
            # \* 'Commercial use subset' of the CORD-19 dataset from
            # [Semantic Scholar](https://pages.semanticscholar.org/coronavirus-research)
            # used, downloaded on 2/Apr/2020. The displayed nodes exclude papers that do not
            # cite and are not cited by others in this set.

            # \* Data analysis carried out for demonstration of data visualisation purposes only.
            # """
                )
            ],
            style={"fontSize": 11, "color": "gray"},
        ),
    ],
    style={"marginTop": 20},
)

app.layout = html.Div([body_layout])  # navbar, 


# def Add_Dash(server):
#     app = dash.Dash(server=server, 
#                     url_base_pathname=url_base,
#                     external_stylesheets=[dbc.themes.BOOTSTRAP])
#     apply_layout_with_auth(app, layout)

@app.callback(
    Output("core_19_cytoscape", "elements"),
    [
        #Input("n_cites_dropdown", "value"),
        Input("element_types_dropdown", "value"),
        # Input("show_edges_radio", "checked"),
        # Input("dim_red_algo", "value"),
        # Input("tsne_perp", "value"),
    ],
)
#def filter_nodes(usr_min_cites, usr_element_types_list, show_edges, dim_red_algo, tsne_perp):
def filter_nodes(usr_element_types_list=None):
    # print(usr_min_cites, usr_element_types_list, show_edges, dim_red_algo, tsne_perp)
    # Use pre-calculated nodes/edges if default values are used
    
    ### TEMP######
    usr_min_cites = 1
    show_edges = False
    dim_red_algo = "umap"
    tsne_perp = 40
    ### TEMP######


    if (
        usr_min_cites == startup_n_cites
        and usr_element_types_list == startup_element_types
        and show_edges == True
        and dim_red_algo == "tsne"
        and tsne_perp == 40
    ):
        logger.info("Using the default element list")
        return startup_elm_list

    else:
        # Generate node list
        #cur_df = network_df[(network_df.n_cites >= usr_min_cites)]
        cur_df = network_df.copy()
        if usr_element_types_list is not None and usr_element_types_list != []:
            cur_df = cur_df[(cur_df['element_type'].isin(usr_element_types_list))]

        position_arr = cur_df.loc[:, vector_colnames].to_numpy()

        cur_node_list = update_node_data(dim_red_algo, tsne_perp, in_df=cur_df, position_arr=position_arr)

        conn_list = []
        # if show_edges:
        #     conn_list = draw_edges(cur_df)

        elm_list = cur_node_list + conn_list

    return elm_list


@app.callback(
    Output("node-data", "children"), [Input("core_19_cytoscape", "mouseoverNodeData")]  # selectedNodeData
)
def display_nodedata(datalist):
    contents = "Click on a node to see its details here"

    # datalist = [datalist]
    # if datalist is not None:
    #     if len(datalist) > 0:
    #         data = datalist[-1]
    print("ssssssssssss")
    data = datalist
    if data is not None:
        contents = []
        contents.append(html.H5("제목: " + data["title"].title()))
        contents.append(
            html.P(
                "출판일: "
                + data["publish_date"]
            )
        )
        contents.append(
            html.P(
                "요약문: "
                + str(data["text_sum"])
            )
        )
        contents.append(
            html.A(
                #id = 'link'+str(index),
                # href=data["url"],
                href='/docs/1',
                children='문서 정보 확인하기', 
                target="_blank",
                
            )                
        )

    return contents

    #return app.server


if __name__ == "__main__":
    app.run_server(debug=False)