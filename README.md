<img style="float: right;" src="asset/workflow.png" width="500">

# LogPrompt

This repo contains codes and the dataset for implementing and evaluating LogPrompt, a prompt engineering toolkit for log analysis with LLMs in software O\&M.

[https://arxiv.org/abs/2311.13246](https://arxiv.org/abs/2308.07610) (ICPC-2024 Long Paper/ ICSE-2024 Poster)


## 📣 Introduction
<p align="center">
    <img src="asset/example.png" width=800 />
</p>

Automated log analysis is crucial in modern software-intensive systems for facilitating program comprehension throughout software maintenance and engineering life cycles. Existing methods perform tasks such as log parsing and log anomaly detection by providing a single prediction value without interpretation. However, given the increasing volume of system events, the limited interpretability of analysis results hinders analysts' comprehension of program status and their ability to take appropriate actions. Moreover, these methods require substantial in-domain training data, and their performance declines sharply (by up to 62.5%) in online scenarios involving unseen logs from new domains, a common occurrence due to rapid software updates. In this paper, we propose LogPrompt, a novel interpretable log analysis approach for online scenarios. LogPrompt employs large language models (LLMs) to perform online log analysis tasks via a suite of advanced prompt strategies tailored for log tasks, which enhances LLMs' performance by up to 380.7% compared with simple prompts. Experiments on nine publicly available evaluation datasets across two tasks demonstrate that LogPrompt, despite requiring no in-domain training, outperforms existing approaches trained on thousands of logs by up to 55.9%. We also conduct a human evaluation of LogPrompt's interpretability, with six practitioners possessing over 10 years of experience, who highly rated the generated content in terms of usefulness and readability (averagely 4.42/5). LogPrompt also exhibits remarkable compatibility with open-source and smaller-scale LLMs, making it flexible for practical deployment.

## 🔰 Installation
```
$ pip install requirements.txt
```
## ✨ Usage

1. First, obtain the API key for ChatGPT (For other LLMs, please modify the API url accordingly).
   
3. Prepare your input logs into a excel file with one column 'log'.
   
5. Specify a prompt strategy from [Self,CoT,InContext]. If InContext is chosen, prepare your labelled log examples into a excel file with two columns: 'log' and 'label'. 'label' should be either 'normal' or 'abnormal'.
   
7. Run by this command:

```
python LogPrompt_code.py --API_KEY YOUR_KEY_HERE --dataset YOUR_INPUT_FILE --strategy YOUR_STRATEGY --output_file_name NAME_OF_OUTPUT --example_file LEAVE_BLANK_IF_NOT_InContext
```

9. This will output two files: first is the raw answers and prompts, second is the aligned logs and answers.
