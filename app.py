#!/usr/bin/python
#-*-coding:utf-8-*-
#Filename: app.py
'''
    This application is designed to show a Knowledge based ChatBot.
    Author: Shiyu Wang
    email: shiyu.wang@alphamol.com
'''

from flask import Flask, render_template, request
import json
import pandas as pd
import openai
import re
import os
import py2neo
from py2neo import Node, Relationship, Graph, Subgraph
from py2neo import NodeMatcher, RelationshipMatcher


reationship_list=["Classifications","G proteins","effectors","tissues","functions",
"diseases","endogenous ligands","drugs","pdbs"]
node_features_list=["wiki","uniprot_function","chembl_id","name","TTD_id","KEGG_id","GeneCard_name"]

# open database
graph = Graph("bolt://localhost:7687/", auth=("neo4j", "kangsijia-neo4j"))
matcher_n = NodeMatcher(graph)
matcher_r = RelationshipMatcher(graph)

#use your own openai api
openai.api_key = "xxxxxxx"

with open("static/name_syno.json") as json_file:
    name_syno_dic=json.load(json_file)

with open("static/name.json") as json_file:
    name_dic=json.load(json_file)


def answer(content):
    previous=[{"role": "system", "content": "You are a helpful assistant."}]
    new_message={"role": "user", "content": content}
    previous.append(new_message)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=previous,
        temperature=0.5
    )
    return response.choices[0].message.content



def process_question(question):
    for name in name_dic:
        if name.lower() in [q.lower() for q in question.split(" ")]:
            break
    if name == "nd":
        for name in name_syno_dic:
            if name.lower() in [q.lower() for q in question.split(" ")]:
                break
    if name == "nd":
        for name in name_syno_dic:
            if name.lower() in question.lower():
                break
    try:
        uniprot=name_dic[name]
    except:
        uniprot=name_syno_dic[name]

    node_features=[]
    relation_features=[]

    pattern = re.compile(r'\"(.*?)\"')
    node_name_list=pattern.findall(question)

    if "uniprot" in question.lower():
        node_features.append("name")
    if "chembl" in question.lower():
        node_features.append("chembl_id")
    if "name" in question.lower():
        node_features.append("GeneCard_name")
    if "ttd" in question.lower() or "therapeutic target database" in question.lower():
        node_features.append("TTD_id")
    if "kegg" in question.lower() or "kyoto encyclopedia of genes and genomes" in question.lower():
        node_features.append("KEGG_id")
    if "g protein" in question.lower() or "g-protein" in question.lower():
        relation_features.append("G proteins")
    if "class" in question.lower():
        relation_features.append("Classifications")
    if "pdb" in question.lower() or "structure" in  question.lower():
        relation_features.append("pdbs")
    if "disease" in question.lower():
        relation_features.append("diseases")
    if "drug" in question.lower():
        relation_features.append("drugs")
    if "ligand" in question.lower() or "bind" in question.lower():
        relation_features.append("endogenous ligands")
    if "tissue" in question.lower() or "distribution" in question.lower():
        relation_features.append("tissues")
    if "pathway" in question.lower():
        relation_features.append("effectors")
        relation_features.append("functions")
    if "function" in question.lower():
        node_features.append("uniprot_function")
        relation_features.append("functions")

    return uniprot, node_features, relation_features, node_name_list

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html',
    data=[{'mode':'hybird mode'}, {'mode':'KG-only mode'}])

@app.route('/', methods=['POST'])
def run_script():
    mode=request.form.get('mode')
    question=request.form['question']
    output={}
    uniprot, node_features, relation_features, node_name_list = process_question(question)
    if mode == "Hybird mode":
        if uniprot == "nd":
            output["ChatGPT answer your question"]=answer(question)
            return render_template('index.html', 
            output=output, 
            question=request.form['question'])
        node = matcher_n.match("receptors").where(name=uniprot).first()
        content=[]
        for n_fea in node_features_list:
            content.append(n_fea+" of this receptor is "+node[n_fea])
        for r_type in reationship_list:
            r_s=matcher_r.match({node}, r_type=r_type)
            tmp=[]
            for r in r_s:
                tmp.append(r.end_node["name"])
            content.append(r_type+" of this receptor follows:"+";".join(tmp))
        question=".\n".join(["\n".join(content),
        "Answer the question:",]).replace(" name "," uniprot code ")+" "+question
        #output["ChatGPT answer your question with the enhanced by GPCR-KG"]=answer(question)
        #output["Supporting information"]=question
        return render_template('index.html', output=output, question=request.form['question'])
    if node_name_list != []:
        for node_name in node_name_list:
            content=[]
            node = matcher_n.match().where(name=node_name).first()
            r_s=list(matcher_r.match({node}))
            for r in  r_s:
                content.append(r.start_node["GeneCard_name"])
            output[node_name] = " ".join([c for c in content if c != None])
        return render_template('index.html', output=output, question=request.form['question'])
    if uniprot == "nd":
        output["output"]="Sorry, I don't have any related information to share with you"
    else:
        node = matcher_n.match("receptors").where(name=uniprot).first()
        output["Wikipedia reminds:"]=node["wiki"]
        for f in node_features:
            output[f]=node[f]
        for f in relation_features:
            content=[]
            r_s=matcher_r.match({node}, r_type=f)
            for r in r_s:
                content.append(r.end_node["name"])
            output[f]=";".join(content)
    return render_template('index.html', output=output, question=request.form['question'])

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        return redirect(url_for('index'))
    return render_template('contact.html')


@app.route('/home', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        return redirect(url_for('index'))

    return render_template('index.html')

@app.route('/tutorial', methods=['GET', 'POST'])
def tutorial():
    if request.method == 'POST':
        return redirect(url_for('index'))

    return render_template('tutorial.html')

if __name__ == '__main__':
    app.run(host = '0.0.0.0' ,port = 5000, debug = 'False')
