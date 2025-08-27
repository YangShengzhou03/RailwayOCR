from paddleocr import PaddleOCR
import os

# 初始化OCR模型，使用新参数替换 deprecated 的 use_angle_cls
ocr = PaddleOCR(use_textline_orientation=True, lang='en')  # 用 use_textline_orientation 替代 use_angle_cls

# 图片路径
image_path = r"D:\待分类\结果\识别失败\IMG_0851.JPG"

# 检查图片文件是否存在
if not os.path.exists(image_path):
    print(f"错误：图片文件不存在 - {image_path}")
else:
    # 进行OCR识别
    result = ocr.predict(image_path)

    # 提取并打印识别结果
    print("识别结果：")
    if result and len(result) > 0:
        for line in result[0]:
            text = line[1][0]
            confidence = line[1][1]
            filtered_text = ''.join([c for c in text if c.isalnum() or c in ' .,-_'])
            print(f"文本: {filtered_text}, 置信度: {confidence:.4f}")
    else:
        print("未识别到任何文本")
