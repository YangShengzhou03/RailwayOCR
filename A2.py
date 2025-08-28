import os
import sys

sys.stderr.reconfigure(encoding='utf-8')

from paddleocr import PaddleOCR


def main():
    try:
        # 初始化OCR模型（使用最新参数，移除冗余配置）
        ocr = PaddleOCR(
            use_textline_orientation=True,
            lang='en'  # 英文识别，若需中文可改为'ch'
        )

        # 使用相对路径或英文路径避免中文编码问题
        image_path = "test_image.jpg"
        
        # 如果默认图片不存在，提示用户输入路径
        if not os.path.exists(image_path):
            print("⚠️  默认图片 test_image.jpg 不存在")
            image_path = input("请输入图片路径: ").strip('"')
            
            if not os.path.exists(image_path):
                print(f"❌ 错误：图片文件不存在 - {image_path}")
                print(f"当前工作目录：{os.getcwd()}")
                return

        # 检查图片是否存在
        if not os.path.exists(image_path):
            print(f"❌ 错误：图片文件不存在 - {image_path}")
            print(f"当前工作目录：{os.getcwd()}")
            print(f"目录下文件列表：{os.listdir(os.getcwd())}")  # 辅助排查文件是否在目录中
            return

        # 执行OCR识别（使用ocr()方法而不是predict()，兼容不同版本）
        print(f"✅ 开始识别图片: {image_path}")
        
        # 尝试两种API调用方式
        try:
            result = ocr.ocr(image_path)
            print("使用 ocr() 方法成功")
        except Exception as e:
            print(f"ocr() 方法失败: {e}")
            try:
                result = ocr.predict(image_path)
                print("使用 predict() 方法成功")
            except Exception as e2:
                print(f"predict() 方法也失败: {e2}")
                raise

        # 解析识别结果（适配不同格式的返回结果）
        print("\n📝 识别结果（置信度≥0.3过滤）：")
        
        if not result:
            print("⚠️  未识别到任何结果")
            return
            
        # 处理不同格式的结果
        if isinstance(result, list) and len(result) > 0:
            # 新版本格式：列表包含OCRResult对象
            first_result = result[0]
            
            if hasattr(first_result, 'rec_texts') and hasattr(first_result, 'rec_scores'):
                # OCRResult对象格式
                rec_texts = first_result.rec_texts
                rec_scores = first_result.rec_scores
            elif isinstance(first_result, dict):
                # 字典格式
                rec_texts = first_result.get('rec_texts', [])
                rec_scores = first_result.get('rec_scores', [])
            else:
                # 传统列表格式
                rec_texts = []
                rec_scores = []
                for word_info in first_result:
                    if len(word_info) >= 2 and isinstance(word_info[1], (list, tuple)) and len(word_info[1]) >= 2:
                        rec_texts.append(str(word_info[1][0]))
                        rec_scores.append(float(word_info[1][1]))
        else:
            print(f"⚠️  未知的结果格式: {type(result)}")
            return

        # 确保文本和置信度长度一致
        if len(rec_texts) != len(rec_scores):
            print(f"⚠️  文本({len(rec_texts)})与置信度({len(rec_scores)})数量不匹配")
            # 取最小长度继续处理
            min_len = min(len(rec_texts), len(rec_scores))
            rec_texts = rec_texts[:min_len]
            rec_scores = rec_scores[:min_len]

        # 过滤空文本和低置信度结果（置信度阈值可调整，如0.3）
        valid_results = [
            (text, score)
            for text, score in zip(rec_texts, rec_scores)
            if text and str(text).strip() != '' and score >= 0.3
        ]

        # 打印有效结果
        if valid_results:
            print(f"找到 {len(valid_results)} 个有效结果:")
            for idx, (text, score) in enumerate(valid_results, 1):
                # 过滤特殊字符（保留数字、字母、常见符号）
                filtered_text = ''.join([c for c in str(text) if c.isalnum() or c in ' :.-_'])
                print(f"  {idx}. 文本：{filtered_text:15} | 置信度：{score:.4f}")
        else:
            print("⚠️  未识别到有效文本（已过滤空文本和低置信度结果）")
            print(f"原始文本: {rec_texts}")
            print(f"原始置信度: {rec_scores}")

    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()