import os
import json
import boto3
import requests
from datetime import datetime, timedelta


def lambda_handler(event, context):
    # 実行日前月のAWS利用コストを取得
    ce_input_day_JST = (datetime.now() + timedelta(hours=9)).replace(day=1)
    ce_input_day_end = ce_input_day_JST - timedelta(days=1)
    ce_input_day_start = (ce_input_day_end - timedelta(days=1)).replace(day=1)
    ce_client = boto3.client('ce')
    monthly_costs_per_group = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': ce_input_day_start.strftime('%Y-%m-%d'),
            'End': ce_input_day_end.strftime('%Y-%m-%d')
        },
        Granularity='MONTHLY',
        Metrics=['AMORTIZED_COST'],
        Filter={
            'Not': {
                'Dimensions': {
                    'Key': 'RECORD_TYPE',
                    'Values': ['Tax']
                }
            } 
                
        },
        GroupBy=[{'Type': 'TAG', 'Key': 'Env'}],
    )['ResultsByTime'][0]['Groups']
    print(monthly_costs_per_group)

    # 取得したコストをEnvタグごとに集計
    env_costs = []
    empty_tag_amount = 0
    allocated_tags_amount = 0
    for item in monthly_costs_per_group:
        amount = float(item['Metrics']['AmortizedCost']['Amount'])
        if item['Keys'][0] == 'Env$':
            env_costs.append(('タグなし', amount))
            empty_tag_amount += amount
        else:
            env_costs.append((item['Keys'][0].replace('Env$', ''), amount))
            allocated_tags_amount += amount
    env_costs.sort(key=lambda x: -x[1])

    # Mattermostへの通知メッセージを作成
    confluence_page_link = "https://confluence.paylabo.com/pages/viewpage.action?pageId=442272030"
    messages = [
        f"### お知らせ AWS [sandbox]({confluence_page_link})アカウント {ce_input_day_start.strftime('%Y-%m')}の使用額",
        "全体規定額:100万円 / 個人規定額:2.5万円",
        "",
        "| user | cost |",
        "|:--|:--|",
        f"|Total amount|${empty_tag_amount + allocated_tags_amount:.2f}|"
    ]
    for env_cost in env_costs:
        messages.append(f"|{env_cost[0]}|${env_cost[1]:.2f}|")
    empty_tag_occupancy = 100 * empty_tag_amount / (empty_tag_amount + allocated_tags_amount)
    messages.append("")
    messages.append(f"タグの付いていないリソースのコスト占有率が **{empty_tag_occupancy:.2f}%** 存在します！")
    messages.append("")
    messages.append(":thanks: sandboxに関するリンクはこちら :thanks:")
    messages.append(f"[{confluence_page_link}]({confluence_page_link})")

    # Mattermost通知
    headers = {'Content-Type': 'application/json'}
    payload = {
        "channel": os.environ['MATTERMOST_CHANNEL'],
        "username": "sandbox-monthly-cost-report-bot",
        "text": "\n".join(messages),
    }
    r = requests.post(os.environ['MATTERMOST_WEBHOOK_URL'], headers=headers, data=json.dumps(payload))
    if r.status_code != 200:
        raise Exception(f"Post failed with status code: {r.status_code}, message: {r.text}")
    return
