from paddleocr import PaddleOCR
import os

# 初始化OCR模型，使用新参数替换 deprecated 的 use_angle_cls
ocr = PaddleOCR(use_textline_orientation=True, lang='en')  # 用 use_textline_orientation 替代 use_angle_cls

# 图片路径 - 使用相对路径避免中文编码问题
image_path = "test_image.jpg"  # 请确保项目目录下有测试图片文件

# 检查图片文件是否存在
if not os.path.exists(image_path):
    print(f"错误：图片文件不存在 - {image_path}")
else:
    # 进行OCR识别
    result = ocr.predict(image_path)

    # 提取并打印识别结果
    print("识别结果：")
    
    if result and len(result) > 0 and hasattr(result[0], 'rec_texts') and result[0].rec_texts:
        # 新的PaddleOCR结果格式 - 从结果对象提取
        for i, text in enumerate(result[0].rec_texts):
            confidence = result[0].rec_scores[i] if i < len(result[0].rec_scores) else 0.0
            filtered_text = ''.join([c for c in text if c.isalnum() or c in ' .,-_'])
            print(f"文本: {filtered_text}, 置信度: {confidence:.4f}")
    else:
        print("未识别到任何文本")
        if result and len(result) > 0:
            print("可用属性:", [attr for attr in dir(result[0]) if not attr.startswith('_')])
