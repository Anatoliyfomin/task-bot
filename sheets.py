import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Подключение (будет использоваться из main.py)
def get_client():
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    return gspread.authorize(creds)

def ensure_header():
    """Создаёт заголовки, если таблица пустая"""
    try:
        client = get_client()
        sheet = client.open_by_key(os.environ.get("spreasheet_id")).sheet1
        if len(sheet.get_all_values()) == 0:
            sheet.append_row(["Дата", "Задача", "Статус", "Дедлайн", "Объект"])
    except:
        pass

def append_task(date, task, deadline, obj_name):
    client = get_client()
    sheet = client.open_by_key(os.environ.get("spreasheet_id")).sheet1
    sheet.append_row([date, task, "Не начато", deadline, obj_name])

def mark_in_progress(row_num):
    client = get_client()
    sheet = client.open_by_key(os.environ.get("spreasheet_id")).sheet1
    sheet.update_cell(row_num, 3, "В работе")

def mark_done(row_num):
    client = get_client()
    sheet = client.open_by_key(os.environ.get("spreasheet_id")).sheet1
    sheet.update_cell(row_num, 3, "Выполнено")

def get_tasks_for_object(obj_name):
    client = get_client()
    sheet = client.open_by_key(os.environ.get("spreasheet_id")).sheet1
    all_data = sheet.get_all_values()
    return [row for row in all_data if len(row) > 4 and row[4] == obj_name]

def search_tasks(query):
    client = get_client()
    sheet = client.open_by_key(os.environ.get("spreasheet_id")).sheet1
    all_data = sheet.get_all_values()
    results = []
    for row in all_data:
        if len(row) > 1 and query.lower() in str(row[1]).lower():
            results.append(row)
    return results

def get_objects():
    client = get_client()
    sheet = client.open_by_key(os.environ.get("spreasheet_id")).sheet1
    all_data = sheet.get_all_values()
    objects = set()
    for row in all_data:
        if len(row) > 4 and row[4]:
            objects.add(row[4])
    return list(objects)
