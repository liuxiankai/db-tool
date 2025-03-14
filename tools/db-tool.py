from collections.abc import Generator
from typing import Any
import psycopg2
import re
import pandas as pd
from decimal import Decimal
from datetime import datetime
import json

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


def _refactor(ans):
    ans = re.sub(r"<think>.*</think>", "", ans, flags=re.DOTALL)
    match = re.search(r"```sql\s*(.*?)\s*```", ans, re.DOTALL)
    if match:
        ans = match.group(1)  # Query content
        return ans
    else:
        print("no markdown")
    ans = re.sub(r'^.*?SELECT ', 'SELECT ', (ans), flags=re.IGNORECASE)
    ans = re.sub(r';.*?SELECT ', '; SELECT ', ans, flags=re.IGNORECASE)
    ans = re.sub(r';[^;]*$', r';', ans)
    if not ans:
        raise Exception("SQL statement not found!")
    return ans
def convert_values(value):
    if isinstance(value, Decimal):
        return float(value)  # 处理 Decimal 类型
    elif isinstance(value, pd.Timestamp):
        return value.strftime('%Y-%m-%d %H:%M:%S')  # 处理 Timestamp 类型
    elif isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')  # 处理 datetime 类型
    return value  # 其他类型保持不变

class DbToolTool(Tool):

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        params = {
            "host": tool_parameters["host"],
            "port": tool_parameters["port"],
            "dbname": tool_parameters["dbname"],
            "username": tool_parameters["username"],
            "password": tool_parameters["password"],
            "query_sql": tool_parameters["query_sql"]
        }

        DB_CONFIG = {
            "host": params["host"],
            "port": params["port"],
            "dbname": params["dbname"],
            "user": params["username"],
            "password": params["password"]
        }

        # 建立数据库连接
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 执行 SQL 查询
        sql = params["query_sql"]
        cursor.execute(sql)
        data = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]  # 获取列名

        # 转换为 Pandas DataFrame
        df = pd.DataFrame(data, columns=columns)
        df = df.applymap(convert_values)  # 处理整个 DataFrame

        # 转换为 JSON
        result = json.dumps(df.to_dict(orient='records'), ensure_ascii=False)

        cursor.close()
        conn.close()
        print(result)
        yield self.create_text_message(result)
