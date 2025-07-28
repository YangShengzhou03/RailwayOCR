import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timedelta

import oss2

main_window = None


def load_config(file_path='Config.json'):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


Config = load_config()


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path).replace(os.sep, '/')


def log(level, message):
    timestamp = time.strftime("%m-%d %H:%M:%S")
    colors = {
        "INFO": "#691bfd",
        "ERROR": "#FF0000",
        "WARNING": "#FFA500",
        "DEBUG": "#008000"
    }
    color = colors.get(level, "#000000")
    formatted_message = f'<span style="color:{color}">[{timestamp}] [{level}] {message}</span>'
    if main_window and hasattr(main_window, 'textEdit_log'):
        main_window.textEdit_log.append(formatted_message)
        main_window.textEdit_log.ensureCursorVisible()


def upload_and_get_signed_url(local_file, oss_path):
    filename = os.path.basename(local_file)
    log("INFO", f"文件就绪: {filename}")
    auth = oss2.Auth(Config["ACCESS_KEY_ID"], Config["ACCESS_KEY_SECRET"])
    bucket = oss2.Bucket(auth, Config["ENDPOINT"], Config["BUCKET_NAME"])
    if not os.path.exists(local_file):
        error_msg = f"文件不存在: {local_file}"
        log("ERROR", error_msg)
        return {'success': False, 'error': error_msg}
    result = bucket.put_object_from_file(oss_path, local_file)
    if result.status == 200:
        signed_url = bucket.sign_url('GET', oss_path, Config["EXPIRES_IN"])
        expire_time = (datetime.now() + timedelta(seconds=Config["EXPIRES_IN"])).strftime("%m-%d %H:%M:%S")
        return {
            'success': True,
            'signed_url': signed_url,
            'expire_time': expire_time
        }
    error_msg = f"OSS处理失败，HTTP状态码: {result.status}"
    log("ERROR", error_msg)
    return {'success': False, 'error': error_msg}


def is_image_file(filename):
    return os.path.splitext(filename)[1].lower() in Config["ALLOWED_EXTENSIONS"]


def parse_ocr_result(ocr_data):
    if not ocr_data.get('success'):
        return None
    data = ocr_data.get('data', '')
    try:
        text = data.get('msg', '') if isinstance(data, dict) else json.loads(data).get('msg', '')
    except (json.JSONDecodeError, TypeError):
        text = str(data)
    match = re.search(Config["RE"], text)
    return match.group(0).upper() if match else None


def process_image_file(local_file_path, client):
    filename = os.path.basename(local_file_path)
    oss_path = f"RailwayOCR/images/{datetime.now().strftime('%Y%m%d')}/{filename}"
    upload_result = upload_and_get_signed_url(local_file_path, oss_path)
    if not upload_result['success']:
        return {'filename': filename, 'success': False, 'error': upload_result['error']}
    log("WARNING", f"正在识别文件: {filename}")
    for attempt in range(Config["RETRY_TIMES"]):
        ocr_result = client.run_workflow(
            workflow_id=Config["WORKFLOW_ID"],
            parameters={
                "prompt": "请识别图像中卡片上由单个英文字母和单个数字组成的组合标签...",
                "image": upload_result['signed_url']
            }
        )
        if ocr_result['success']:
            recognition = parse_ocr_result(ocr_result)
            status = {'filename': filename, 'success': bool(recognition), 'recognition': recognition,
                      'oss_path': oss_path, 'signed_url': upload_result['signed_url']}
            log("DEBUG" if recognition else "WARNING",
                f"识别结果: {filename} → {recognition}" if recognition else f"未识别到有效标签: {filename}")
            return status
        time.sleep(1)
    error_msg = ocr_result.get('error_msg', '未知识别错误') if ocr_result else '未获取到识别结果'
    log("ERROR", f"Ai识别失败: {filename}，原因: {error_msg}")
    return {'filename': filename, 'success': False, 'error': error_msg}


def create_output_directories(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "识别失败"), exist_ok=True)


def copy_to_classified_folder(local_file_path, recognition, output_dir, is_move=False):
    filename = os.path.basename(local_file_path)
    category = ''.join(c for c in recognition if c.isalnum() or c in "-_.() ") if recognition else "识别失败"
    category_dir = os.path.join(output_dir, category or "其他")
    os.makedirs(category_dir, exist_ok=True)
    dest_path = os.path.join(category_dir, filename)
    counter = 1
    while os.path.exists(dest_path):
        name, ext = os.path.splitext(filename)
        dest_path = os.path.join(category_dir, f"{name}_{counter}{ext}")
        counter += 1
    try:
        (shutil.move if is_move else shutil.copy2)(local_file_path, dest_path)
        log("INFO", f"文件已{'移动' if is_move else '复制'}: {filename} → {category_dir}")
        return category_dir
    except Exception as e:
        log("ERROR", f"文件操作失败: {filename}, 错误: {str(e)}")
        return None


def save_summary(results, output_dir):
    os.makedirs(Config["SUMMARY_DIR"], exist_ok=True)
    summary_path = os.path.join(Config["SUMMARY_DIR"], "summary.json")
    stats_path = os.path.join(Config["SUMMARY_DIR"], "statistics.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    total = len(results)
    success_count = sum(1 for r in results if r['success'])
    stats = {
        "处理时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "总文件数": total,
        "成功识别": success_count,
        "识别失败": total - success_count,
        "识别成功率": f"{success_count / total * 100:.2f}%" if total > 0 else "0.00%",
        "类别分布": {r['recognition']: sum(1 for x in results if x['recognition'] == r['recognition'])
                     for r in results if r['success']}
    }
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    return stats
