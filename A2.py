import os
import sys

# 解决中文乱码问题
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from paddleocr import PaddleOCR


def main():
    try:
        # 初始化OCR模型（使用最新参数，移除冗余配置）
        ocr = PaddleOCR(
            use_textline_orientation=True,
            lang='en'  # 英文识别，若需中文可改为'ch'
        )

        # 图片路径（确保路径正确，建议用英文路径）
        image_path = "test_image.jpg"

        # 检查图片是否存在
        if not os.path.exists(image_path):
            print(f"❌ 错误：图片文件不存在 - {image_path}")
            print(f"当前工作目录：{os.getcwd()}")
            print(f"目录下文件列表：{os.listdir(os.getcwd())}")  # 辅助排查文件是否在目录中
            return

        # 执行OCR识别（模型已自动加载，无需额外配置）
        print(f"✅ 开始识别图片: {image_path}")
        result = ocr.predict(image_path)

        # 解析识别结果（重点适配字典格式的返回结果）
        print("\n📝 识别结果（置信度≥0.3过滤）：")
        # 遍历结果列表（每张图片对应一个字典）
        for img_result in result:
            # 提取关键字段（rec_texts：文本，rec_scores：置信度）
            rec_texts = img_result.get('rec_texts', [])
            rec_scores = img_result.get('rec_scores', [])

            # 确保文本和置信度长度一致
            if len(rec_texts) != len(rec_scores):
                print("⚠️  文本与置信度数量不匹配，跳过解析")
                continue

            # 过滤空文本和低置信度结果（置信度阈值可调整，如0.3）
            valid_results = [
                (text, score)
                for text, score in zip(rec_texts, rec_scores)
                if text.strip() != '' and score >= 0.3
            ]

            # 打印有效结果
            if valid_results:
                for idx, (text, score) in enumerate(valid_results, 1):
                    # 可选：过滤特殊字符（保留数字、字母、常见符号）
                    filtered_text = ''.join([c for c in text if c.isalnum() or c in ' :.-_'])
                    print(f"  {idx}. 文本：{filtered_text:10} | 置信度：{score:.4f}")
            else:
                print("⚠️  未识别到有效文本（已过滤空文本和低置信度结果）")

    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()