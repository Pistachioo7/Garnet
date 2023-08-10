import sys

import pandas as pd
from datetime import datetime
import re
import queue
import argparse




def convert_to_seconds(date_str):
    date_format = "%Y-%m-%d %H:%M:%S"
    date_obj = datetime.strptime(date_str, date_format)
    return int(date_obj.timestamp())


def convert_to_inttime(date_str):
    # 提取日期部分并删除短划线
    date_only = date_str.split()[0].replace('-', '')
    # 转换为整数
    date_num = int(date_only)
    return date_num


def delete_letter(date_str):
    result = re.sub(r'[a-zA-Z]', '', date_str)
    return int(result)


def process_each_person(data):
    data = data.sort_values(by=['秒时间'], ascending=[True])
    data = data.reset_index(drop=True)
    q = queue.Queue()
    count = 0
    result = pd.DataFrame(columns=data.columns)
    for index, row in data.iterrows():
        while (not q.empty()) and (row['秒时间'] - q.queue[0]['秒时间'] > check_time):
            if count < 5:
                ele = q.get()
                count = count - ele['倍数']
            else:
                count = 0
                while not q.empty():
                    ele = q.get()
                    count = count + ele['倍数']
                    ele['累积倍数'] = count
                    if count >= 5:
                        result = result.append(ele, ignore_index=True)
                count = 0
        count = count + row['倍数']
        q.put(row)
    return result


def process(file_path):
    data = pd.read_excel(file_path, engine='openpyxl')
    data = data[data['是否领药'] == '是']  # 删除未领药字段
    data = data.drop_duplicates(subset=['处方单号'])  # 删除重复的字段
    data['整数日期'] = data['开具时间'].apply(convert_to_inttime)
    data['倍数'] = data['标准开药量（mg）'] / (14 * data['标准用药量（mg）'])
    data['秒时间'] = data['开具时间'].apply(convert_to_seconds)
    data['处方单号'] = data['处方单号'].apply(delete_letter)
    data['累积倍数'] = 0
    ids = data['患者证件号'].unique()
    result = pd.DataFrame(columns=data.columns)
    for id in ids:
        personal_data = process_each_person(data[data['患者证件号'] == id])
        result = pd.concat([result, personal_data], ignore_index=True)
    result = result[['处方单号', '患者证件号', '整数日期', '累积倍数'] ]
    result['累积倍数'] = (result['累积倍数'] * 100).astype(int)

    file = open("./Player-Data/Input-P1-0", 'w')
    for index, row in result.iterrows():
        file.write(" ".join(str(v) for v in row) + "\n")
    file.close()
    num_rows, num_cols = result.shape

    print(f"行数: {num_rows}")
    print(f"列数: {num_cols}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Drug data process')
    parser.add_argument('--filepath', type=str, default="./Data/drug.xlsx", help='The path of excel file')
    parser.add_argument('--checkdays', type=int, default=14,  help='The continue days to check')
    parser.add_argument('--threshold', type=float, default=5,  help='The threshold for judgement')

    args = parser.parse_args()
    check_time = args.checkdays * 24 * 60 * 60
    threshold = args.threshold
    process(args.filepath)