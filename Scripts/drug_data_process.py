import pandas as pd
from datetime import datetime
import re

check_days = 14
check_time = check_days * 24 * 60 * 60
threshold = 5.0

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
    for index, row in data.iterrows():
        count = 0
        end_index = index
        for index2, row2 in data.iloc[index:].iterrows():
            if row2['秒时间'] - row['秒时间'] > check_time:
                end_index = index2
                break
            count = count + row2['倍数']
        if count >= threshold:
            for index2, row2 in data.iloc[index:end_index].iterrows():
                data.at[index2, '是否异常'] = 1
    data = data[data['是否异常'] == 1]

    return data

def process(file_path):
    data = pd.read_excel(file_path, engine='openpyxl')
    data = data[data['是否领药'] == '是']
    data['整数日期'] = data['开具时间'].apply(convert_to_inttime)
    data['倍数'] = data['标准开药量（mg）'] / (14 * data['标准用药量（mg）'])
    data['秒时间'] = data['开具时间'].apply(convert_to_seconds)
    data['处方单号'] = data['处方单号'].apply(delete_letter)
    data['是否异常'] = 0
    data['标准开药量（mg）'] = (data['标准开药量（mg）'] *10).astype(int)
    data['标准用药量（mg）'] = (data['标准用药量（mg）']*10).astype(int)
    ids = data['患者证件号'].unique()
    result = pd.DataFrame(columns=data.columns)
    for id in ids:
        personal_data = process_each_person(data[data['患者证件号'] == id])
        result = pd.concat([result, personal_data], ignore_index=True)
    result = result[['处方单号', '患者证件号', '整数日期', '标准开药量（mg）', '标准用药量（mg）'] ]
    file = open("./Player-Data/Input-P1-0", 'w')
    for index, row in result.iterrows():
        file.write(" ".join(str(v) for v in row) + "\n")
    num_rows, num_cols = result.shape

    print(f"行数: {num_rows}")
    print(f"列数: {num_cols}")


if __name__ == '__main__':
    process("./Data/drug.xlsx")