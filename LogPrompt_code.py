import pandas as pd
import textwrap
from typing import List
from tqdm import tqdm
import time
import re
import warnings
import requests
import json
import argparse
import numpy as np
parser=argparse.ArgumentParser()
parser.add_argument('--API_KEY',type=str)#Specify your API key here
parser.add_argument('--dataset',type=str)#excel file path, with column 'log' containing rows of raw logs
parser.add_argument('--strategy',type=str)#prompt strategies, choice between [Self,CoT,InContext]
parser.add_argument('--output_file_name',type=str,default="result.xlsx")
parser.add_argument('--example_file',type=str,default='')# example file for the in-context prompt, a excel file with two columns: [log, label]. The label column should be "normal" or "abnormal".
args=parser.parse_args()
API_URL="https://api.openai.com/v1/chat/completions"#The offical API for GPT-3.5-turbo
OPENAI_API_KEY=args.API_KEY
INPUT_FILE=args.dataset
PROMPT_STRATEGIES=args.strategy
OUTPUT_FILE=args.output_file_name
EXAMPLE_FILE=args.example_file
warnings.simplefilter(action='ignore', category=FutureWarning)
def filter_special_chars_for_F1(s):
    special_chars = r'[^\w\s*]'
    filtered_str = re.sub(special_chars, '', s)
    return filtered_str
def filter_special_characters(input_string):
    return re.sub(r'[^\w\s]', '', input_string).replace('true','').replace('false','')

def generate_prompt(prompt_header,logs: List[str],max_len=1000,no_reason=False) -> List[str]:
    prompt_parts_count=[]
    prompt_parts = []
    prompt=prompt_header
    log_count=0
    startStr=""
    for i, log in enumerate(logs):
        if no_reason:
            startStr+="("+str(i+1)+"x\n"
        else:
            startStr+="("+str(i+1)+"x-y\n"
        log_str = f"({i+1}) {log}"
        log_length = len(log_str)
        prompt_length=len(prompt)
        if log_length > max_len:
            print("warning: this log is too long")

        if prompt_length + log_length <= max_len:
            prompt += f" {log_str}"
            prompt_length += log_length + 1
            log_count+=1
            if i<(len(logs)-1) and (prompt_length+len(logs[i+1]))>=max_len:
                prompt_parts.append(prompt.replace("!!FormatControl!!",startStr).replace("!!NumberControl!!",str(log_count)))
                prompt_parts_count.append(log_count)
                log_count=0
                prompt=prompt_header
                startStr=""
                continue
            if i== (len(logs)-1):
                prompt_parts.append(prompt.replace("!!FormatControl!!",startStr).replace("!!NumberControl!!",str(log_count)))
                prompt_parts_count.append(log_count)
        else:
            if prompt!=prompt_header:
                log_count+=1
                prompt+=f" {log_str}"
                prompt_parts.append(prompt.replace("!!FormatControl!!",startStr).replace("!!NumberControl!!",str(log_count)))
                prompt_parts_count.append(log_count)
            else:
                prompt=prompt.replace("!!FormatControl!!",startStr)
                prompt=f"{prompt} ({i+1}) {log}"
                prompt_parts.append(prompt)
                prompt_parts_count.append(1)
            log_count=0
            prompt=prompt_header
            startStr=""
    return prompt_parts,prompt_parts_count

def filter_numbers(text):
    pattern = r'\(\d+\)'
    return re.sub(pattern, '', text)
def reprompt(raw_file_name,j,df_raw_answer,temperature):
    URL=API_URL
    headers={'Content-Type':'application/json','Authorization':f'Bearer {OPENAI_API_KEY}'}
    prompt=df_raw_answer.loc[j,"prompt"]
    msgs=[]
    payload={
        "model":"gpt-3.5-turbo",
        "temperature":temperature,
        "top_p":1,
        "n":1,
        "stream":False,
        "stop":None,
        "presence_penalty":0,
        "frequency_penalty":0,
        "logit_bias":{}
            }

    msgs.append({'role':"user","content":prompt})
    payload["messages"]=msgs
    parsed_log=""
    while parsed_log =='':
        try:
            response=requests.request("POST",URL,headers=headers,data=json.dumps(payload))
            res=response.json()
            if "choices" not in res:
                continue
            parse_logs=res["choice"][0]["message"]["content"]
        except Exception as e:
            print("error!")
            print(e)

    df_raw_answer.loc[j,"answer"]=parsed_log
    df_raw_answer.to_excel(raw_file_name,index=False)
    return parsed_log

def parse_logs(raw_file_name,prompt_parts: List[str],prompt_parts_count) -> List[str]:
    parsed_logs = []
    URL=API_URL
    headers={'Content-Type':'application/json','Authorization':f'Bearer {OPENAI_API_KEY}'}
    for p,prompt in tqdm(enumerate(prompt_parts)):
        msgs=[]
        payload={
            "model":"gpt-3.5-turbo",
            "temperature":0.5,
            "top_p":1,
            "n":1,
            "stream":False,
            "stop":None,
            "presence_penalty":0,
            "frequency_penalty":0,
            "logit_bias":{}
                }
        log_count=prompt_parts_count[p]
        msgs.append({'role':"user","content":prompt})
        payload["messages"]=msgs
        parsed_log=""
        while parsed_log =='':
            try:
                response=requests.request("POST",URL,headers=headers,data=json.dumps(payload))
                res=response.json()
                if "choices" not in res:
                    continue
                parse_logs=res["choice"][0]["message"]["content"]
            except Exception as e:
                print("error!")
                print(e)

        parsed_logs.append(parsed_log)

    pd.DataFrame(data=list(zip(prompt_parts,parsed_logs)),columns=['prompt','answer']).to_excel(raw_file_name)
    return parsed_logs

def extract_log_index(prompts):
    log_numbers=[]
    for prompt in prompts:
        log_number=re.findall(r'\((\d{1,4})\)',prompt.split("Organize your answer to be the following format")[1].split('a binary choice between')[0])
        log_numbers.append(sorted(list(set([int(x) for x in log_number]))))
    return log_numbers

def write_to_excel(raw_file_name,df_raw_answer: pd.DataFrame, logs: List[str]) -> tuple:
    reprompt_num=0
    prompts=df_raw_answer['prompt'].tolist()
    log_numbers=extract_log_index(prompts)
    parsed_logs=df_raw_answer['answer'].tolist()
    parsed_logs_per_log = []
    for i, parsed_log in enumerate(parsed_logs):
        log_parts = parsed_log
        parsed_logs_per_log.append(log_parts)
        
    parsed_logs_df = pd.DataFrame()
    index=0
    for j, parsed_log in tqdm(enumerate(parsed_logs_per_log)):
        while 1:
            temperature=0.5
            try:
                pattern = r"\({0}\).*?\({1}\)"
                xx_list=[]
                log_number=log_numbers[j]
                for i in range(len(log_number)-1):
                    start=log_number[i]
                    end=log_number[i+1]
                    if start!=end-1:
                        print('start:',start,'end:',end)
                        continue
                    match=re.search(pattern.format(start,end),parsed_log.replace('\n',''))
                    xx=match.group().split(f"({start})")[1].split(f"({end})")[0].strip()
                    xx_list.append(xx)
                last_log_number=log_number[-1]
                pattern=r"\({0}\).*".format(last_log_number)
                match=re.search(pattern,parsed_log.replace('\n',''))
                xx=match.group().split(f"({last_log_number})")[1].strip()
                xx_list.append(xx)
                for parsed_log_part in xx_list:
                    if parsed_log_part ==None or parsed_log_part=="":
                        continue
                    pred_raw=filter_numbers(parsed_log_part.replace('<*>','')).strip(' ')
                    pred_label=pred_raw
                    parsed_logs_df=parsed_logs_df.append({'log':logs[index],'pred':pred_label},ignore_index=True)
                    index+=1
                break
            except Exception as e:
                print(e,"reprompting...")
                temperature+=0.4
                parsed_log=reprompt(raw_file_name,j,df_raw_answer,temperature)
    
    parsed_logs_df.to_excel('Aligned_'+raw_file_name,index=False)
    
if __name__ == "__main__":
    df = pd.read_excel(INPUT_FILE)
    np.random.seed(123)
    if PROMPT_STRATEGIES == 'CoT':
        df=df.sample(frac=1).reset_index(drop=True)
        answer_desc="a binary choice between normal and abnormal"
        prompt_header="Classify the given log entries into normal an abnormal categories. Do it with these steps: \
        (a) Mark it normal when values (such as memory address, floating number and register value) in a log are invalid. \
        (b) Mark it normal when lack of information. (c) Never consider <*> and missing values as abnormal patterns. \
        (d) Mark it abnormal when and only when the alert is explicitly expressed in textual content (such as keywords like error or interrupt). \
        Concisely explain your reason for each log. Organize your answer to be the following format: !!FormatControl!!, where x is %s and y is the reason. \
        There are !!NumberControl!! logs, the logs begin: "%(answer_desc)
        logs=df['log'].tolist()
        ########### generate prompts ######################
        prompt_parts,prompt_parts_count = generate_prompt(prompt_header,logs,max_len=3000)
        ########### obtain raw answers from GPT ###########
        parse_logs = parse_logs(OUTPUT_FILE,prompt_parts,prompt_parts_count)
        ########### Align each log with its results #######
        df_raw_answer = pd.read_excel(OUTPUT_FILE)
        write_to_excel(OUTPUT_FILE,df_raw_answer,logs)
    if PROMPT_STRATEGIES == 'InContext':
        df_examples=pd.read_excel(EXAMPLE_FILE)
        df=df.sample(frac=1).reset_index(drop=True)
        answer_desc="a binary choice between 0 and 1"
        examples=' '.join(["(%d) Log: %s. Category: %s"%(i+1,df_examples.loc[i,'log'],int(df_examples.loc[i,'label']=='abnormal')) for i in range(len(df_examples))])
        prompt_header="Classify the given log entries into 0 and 1 categories based on semantic similarity to the following labelled example logs: %s.\
        Organize your answer to be the following format: !!FormatControl!!, where x is %s. There are !!NumberControl!! logs, the logs begin: "%(examples,answer_desc)
        logs=df['log'].tolist()
        ########### generate prompts ######################
        prompt_parts,prompt_parts_count = generate_prompt(prompt_header,logs,max_len=3000,no_reason=True)
        ########### obtain raw answers from GPT ###########
        parse_logs = parse_logs(OUTPUT_FILE,prompt_parts,prompt_parts_count)
        ########### Align each log with its results #######
        df_raw_answer = pd.read_excel(OUTPUT_FILE)
        write_to_excel(OUTPUT_FILE,df_raw_answer,logs)        
    if PROMPT_STRATEGIES == "Self":
        #candidate selection
        df=df[:100]
        prompt_candidates=[]
        with open('prompt_candidates.txt') as f:
            for line in f.readlines():
                prompt_candidates.append(line.strip('\n'))
        for i,prompt_candidate in tqdm(enumerate(prompt_candidates)):
            print('prompt %d'%(i+1))
            answer_desc="a parsed log template"
            prompt_header = "%s Organize your answer to be the following format: !!FormatControl!!, where x is %s. There are !!NumberControl!! logs, the logs begin: "%(prompt_candidate,answer_desc)
            logs=df['log'].tolist()
            ########### generate prompts ######################
            prompt_parts,prompt_parts_count = generate_prompt(prompt_header,logs,max_len=3000,no_reason=True)
            ########### obtain raw answers from GPT ###########
            parse_logs = parse_logs('Candidate_%d_'%(i+1)+OUTPUT_FILE,prompt_parts,prompt_parts_count)
            ########### Align each log with its results #######
            df_raw_answer = pd.read_excel(OUTPUT_FILE)
            write_to_excel('Candidate_%d_'%(i+1)+OUTPUT_FILE,df_raw_answer,logs)   
