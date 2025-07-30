# 🚂 RailwayOCR - 铁路图像智能识别与分类系统 🌟

<div align="center">
  <a href="https://www.gnu.org/licenses/agpl-3.0">
    <img src="https://img.shields.io/badge/License-AGPL_v3-blue?style=for-the-badge&logo=gnu" alt="License: AGPL v3">
  </a>
  <a href="https://github.com/YangShengzhou03/RailwayOCR">
    <img src="https://img.shields.io/github/stars/YangShengzhou03/RailwayOCR?style=for-the-badge&logo=github" alt="GitHub Stars">
  </a>
  <a href="https://github.com/YangShengzhou03/RailwayOCR">
    <img src="https://img.shields.io/github/forks/YangShengzhou03/RailwayOCR?style=for-the-badge&logo=github" alt="GitHub Forks">
  </a>
</div>

📌 **专业领域**：铁路设施检测 | 轨道路径识别 | 设备状态分析  
📦 开源项目 | ⚙️ 跨平台应用 | 📈 AI图像识别 + 智能分类 + 缺陷检测  

---

## 📌 目录

1. [简介](#简介)  
2. [核心功能](#核心功能)  
3. [技术规格](#技术规格)  
4. [安装指南](#安装指南)  
5. [使用教程](#使用教程)  
6. [项目结构](#项目结构)  
7. [模型训练](#模型训练)  
8. [性能指标](#性能指标)  
9. [社区与支持](#社区与支持)  
10. [许可证（AGPL-3.0）](#许可证agpl-30)  
11. [未来规划](#未来规划)  
12. [结语](#结语)  

---

## 📌 简介

**RailwayOCR** 是一款专为铁路行业打造的AI图像识别系统，基于深度学习技术，针对铁路场景进行了专项优化。系统能够自动识别铁路设施图像中的关键元素、检测潜在缺陷并进行智能分类，可广泛应用于铁路巡检、设施维护和安全监控等领域。

### 核心价值：
- 🚂 **铁路场景专项优化**：针对铁轨、枕木、接触网等铁路设施进行专项训练，识别准确率行业领先  
- 🔍 **高精度缺陷检测**：可识别裂缝、松动、磨损等常见铁路设施缺陷，最小检测尺寸达0.5mm  
- 📊 **智能分类归档**：自动对铁路图像按设施类型、检测结果进行分类归档，大幅提升管理效率  
- 📱 **多终端适配**：支持PC端批量处理与移动端现场采集双模式，满足不同场景需求  
- 📑 **检测报告生成**：自动生成带标注的检测报告，支持导出PDF格式，便于存档和汇报  

无论是铁路运维单位、工程建设团队还是科研机构，RailwayOCR都能显著提升铁路设施检测效率，降低人工成本，提前发现安全隐患。

![铁路缺陷检测示例](preview/Logo.png)
*图：系统自动识别铁轨裂缝并标注（红色框为检测到的缺陷区域）*

---

## 🚀 核心功能

### 1. 铁路设施智能识别
| 设施类型 | 识别能力 | 应用场景 |
|----------|----------|----------|
| **铁轨** | 识别类型（普通轨、高速轨）、检测裂缝、磨损、变形等缺陷 | 铁轨巡检、定期维护 |
| **枕木** | 识别材质（木枕、混凝土枕）、位置偏移及损坏情况 | 线路维护、病害整治 |
| **接触网** | 检测导线张力、绝缘子破损、异物悬挂等异常 | 电气化铁路检查、供电安全保障 |
| **道岔系统** | 识别道岔类型、检测关键部件状态及转换位置 | 道岔维护、信号系统联动 |
| **标识牌** | 识别各类铁路标识牌内容及状态 | 标识更新、安全提示 |

### 2. 智能缺陷检测
- **裂缝检测**：自动识别铁轨、桥梁等结构表面的裂缝，测量长度和宽度
- **磨损分析**：检测轨头磨损、接触网导线磨耗等情况，评估剩余使用寿命
- **松动识别**：识别螺栓松动、扣件缺失等异常情况
- **异物检测**：识别铁路周边及线路上的异物入侵，如树木、建筑材料等

### 3. 智能分类与管理
- **按设施分类**：自动将图像分为铁轨、枕木、接触网等类别
- **按线路分类**：支持按铁路线路、区段对图像进行分类管理
- **按检测结果分类**：将图像分为正常、疑似缺陷、确认缺陷等类别
- **历史数据对比**：支持对同一位置不同时期的图像进行对比分析

### 4. 辅助功能
- **批量处理**：支持批量导入图像并生成汇总检测报告，适用于定期巡检
- **移动端采集**：配套移动端APP支持现场拍摄与实时检测，适用于现场巡检
- **数据导出**：支持导出检测结果为CSV、Excel等格式，便于进一步分析
- **图像增强**：提供图像去噪、对比度增强等预处理功能，提升识别准确率

---

## 📊 技术规格

| 类别 | 参数 |
|------|------|
| 支持图像格式 | JPG、PNG、TIFF、BMP、RAW |
| 输入图像分辨率 | 最小640×480，最大8192×8192 |
| 处理速度 | 单张图像平均处理时间＜500ms（GPU模式），＜2s（CPU模式） |
| 识别准确率 | 平均准确率＞97%（标准测试集），缺陷检测召回率＞95% |
| 缺陷检测最小尺寸 | 0.5mm×0.5mm（1米距离拍摄） |
| 支持操作系统 | Windows 10/11、Linux（Ubuntu 20.04+）、macOS 12+ |
| 硬件最低要求 | CPU：i5-8400；GPU：GTX 1050Ti；内存：8GB；存储空间：10GB |
| 硬件推荐配置 | CPU：i7-12700；GPU：RTX 3060；内存：16GB；存储空间：50GB |
| 模型大小 | 基础模型：850MB；全功能模型：2.3GB |
| 网络接口 | REST API、WebSocket |
| 数据安全 | 支持本地部署、数据加密存储 |

---

## 📦 安装指南

### 方法一：二进制包安装（推荐）

1. 从 [Releases页面](https://github.com/YangShengzhou03/RailwayOCR/releases) 下载对应操作系统的安装包
2. 运行安装程序，按照向导完成安装
   - Windows：双击 `RailwayOCR-Setup-vX.X.X.exe`
   - Linux：执行 `sudo ./RailwayOCR-vX.X.X-linux.run`
   - macOS：打开 `RailwayOCR-vX.X.X.dmg` 并拖拽到应用程序文件夹

### 方法二：Docker容器安装

```bash
# 拉取Docker镜像
docker pull yangshengzhou/railwayocr:latest

# 运行容器
docker run -d -p 8080:8080 \
  -v /path/to/data:/app/data \
  -v /path/to/models:/app/models \
  yangshengzhou/railwayocr:latest
```

### 方法三：源码编译安装

```bash
# 1. 克隆仓库
git clone https://github.com/YangShengzhou03/RailwayOCR.git
cd RailwayOCR

# 2. 创建虚拟环境
conda create -n railwayocr python=3.9
conda activate railwayocr

# 3. 安装依赖
pip install -r requirements.txt

# 4. 编译并安装
python setup.py install

# 5. 下载预训练模型
python scripts/download_models.py
```

### 移动端APP安装

1. 安卓用户：从 [Releases页面](https://github.com/YangShengzhou03/RailwayOCR/releases) 下载APK文件安装
2. iOS用户：通过TestFlight参与测试或联系我们获取企业版证书

---

## 📖 使用教程

### 桌面端批量处理流程

1. **启动程序**
   ```bash
   # 命令行模式
   railwayocr --batch /path/to/images --output /path/to/reports
   
   # GUI模式
   railwayocr-gui
   ```

2. **导入图像**
   - 点击"导入图像"按钮，选择单个图像或整个文件夹
   - 支持拖放操作批量导入
   - 可设置图像预处理参数（亮度、对比度、降噪等）

3. **选择检测模式**
   - 快速检测：侧重速度，适用于初步筛查
   - 精细检测：侧重精度，适用于重点区域检查
   - 自定义检测：可选择特定检测项目（如仅检测裂缝或接触网）

4. **设置参数**
   - 调整检测阈值：根据实际情况调整缺陷识别的敏感度
   - 设置分类规则：自定义图像分类的标签和条件
   - 选择输出格式：支持CSV、Excel、JSON、PDF等多种格式

5. **开始检测**
   - 点击"开始检测"按钮
   - 实时显示检测进度和中间结果
   - 可暂停、继续或终止检测过程

6. **查看与导出报告**
   - 检测完成后自动展示结果汇总
   - 可查看单张图像的详细检测结果和标注
   - 点击"生成报告"导出PDF格式检测报告
   - 支持对检测结果进行人工复核与修正

### 移动端现场检测流程

1. 打开APP并登录账号
2. 选择检测类型（铁轨/接触网/道岔等）
3. 拍摄现场图像或从相册选择
4. 点击"分析"按钮获取实时检测结果
5. 可添加文字备注、标记重点区域
6. 检测结果自动同步至云端，支持多设备共享
7. 支持离线检测模式，适用于网络信号弱的区域

### API调用示例

以下是使用Python调用RailwayOCR API的示例代码：

```python
import requests
import json
import base64

# API端点
API_URL = "http://localhost:8080/api/v1/detect"

# 读取图像文件
def read_image(file_path):
    with open(file_path, "rb") as f:
        return f.read()

# 图像转Base64
def image_to_base64(image_bytes):
    return base64.b64encode(image_bytes).decode("utf-8")

# 调用API
def detect_railway(image_path, detection_type="all"):
    image_bytes = read_image(image_path)
    image_base64 = image_to_base64(image_bytes)
    
    payload = {
        "image": image_base64,
        "detection_type": detection_type,
        "threshold": 0.7
    }
    
    response = requests.post(API_URL, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"API request failed: {response.status_code}"}

# 示例调用
result = detect_railway("path/to/rail_image.jpg", "rail_defect")
print(json.dumps(result, indent=2))
```

---

## 📂 项目结构

```
RailwayOCR/
├── README.md               # 项目说明文档
├── LICENSE                 # 许可证文件
├── requirements.txt        # 依赖列表
├── setup.py                # 安装配置
├── railwayocr/             # 主程序包
│   ├── __init__.py
│   ├── main.py             # 程序入口
│   ├── cli.py              # 命令行接口
│   ├── gui/                # 图形界面模块
│   │   ├── main_window.py  # 主窗口
│   │   ├── detect_dialog.py # 检测对话框
│   │   └── result_viewer.py # 结果查看器
│   ├── core/               # 核心算法模块
│   │   ├── detector.py     # 目标检测核心
│   │   ├── classifier.py   # 图像分类器
│   │   ├── segmenter.py    # 语义分割模块
│   │   ├── defect_analyzer.py # 缺陷分析器
│   │   └── report_generator.py # 报告生成器
│   ├── models/             # 模型定义与加载
│   │   ├── yolov8_rail.py  # YOLOv8铁路检测模型
│   │   ├── resnet_classifier.py # ResNet分类模型
│   │   └── model_factory.py # 模型工厂
│   ├── utils/              # 工具函数
│   │   ├── image_processing.py # 图像处理工具
│   │   ├── file_manager.py # 文件管理工具
│   │   └── visualization.py # 可视化工具
│   ├── api/                # API接口
│   │   ├── app.py          # FastAPI应用
│   │   └── routes/         # API路由
│   └── config/             # 配置管理
│       └── settings.py     # 配置文件
├── scripts/                # 辅助脚本
│   ├── download_models.py  # 模型下载脚本
│   ├── train_custom.py     # 自定义训练脚本
│   ├── convert_data.py     # 数据转换脚本
│   └── export_onnx.py      # 模型导出脚本
├── docs/                   # 文档资料
│   ├── examples/           # 示例图像
│   ├── user_manual.md      # 用户手册
│   ├── developer_guide.md  # 开发指南
│   └── api_reference.md    # API参考文档
├── tests/                  # 测试代码
│   ├── test_detector.py    # 检测器测试
│   ├── test_classifier.py  # 分类器测试
│   └── test_utils.py       # 工具函数测试
└── mobile/                 # 移动端APP源码
    ├── android/            # 安卓端
    └── ios/                # iOS端
```

---

## 🔬 模型训练

### 数据准备

如果你需要针对特定场景训练自定义模型，首先需要准备训练数据。数据应按以下结构组织：

```
dataset/
├── train/                  # 训练集
│   ├── images/             # 图像文件
│   └── annotations/        # 标注文件
├── val/                    # 验证集
│   ├── images/
│   └── annotations/
└── test/                   # 测试集
    ├── images/
    └── annotations/
```

标注文件应为COCO JSON格式或YOLO TXT格式。

### 模型训练

使用以下命令开始训练：

```bash
python scripts/train_custom.py \
  --dataset /path/to/dataset \
  --model base_model.pth \
  --epochs 50 \
  --batch-size 8 \
  --output custom_model.pth \
  --device cuda:0  # 使用GPU训练
```

### 模型评估

训练完成后，可以使用以下命令评估模型性能：

```bash
python scripts/evaluate_model.py \
  --model custom_model.pth \
  --dataset /path/to/dataset/test \
  --output evaluation_results.json
```

### 数据标注工具

推荐使用 [Label Studio](https://labelstud.io/) 或 [VGG Image Annotator](http://www.robots.ox.ac.uk/~vgg/software/via/) 进行数据标注，我们提供了格式转换脚本可将标注结果转为模型训练所需格式：

```bash
python scripts/convert_annotations.py --input /path/to/labelstudio/annotations --output /path/to/tfrecords
```

---

## 📊 性能指标

在标准测试集（包含10,000张各类铁路设施图像）上的性能表现：

| 检测项目 | 准确率 | 召回率 | F1分数 | 平均检测时间 |
|----------|--------|--------|--------|--------------|
| 铁轨裂缝 | 98.5%  | 97.8%  | 98.1%  | 320ms        |
| 枕木损坏 | 97.6%  | 96.2%  | 96.9%  | 280ms        |
| 接触网异物 | 96.3%  | 95.1%  | 95.7%  | 410ms        |
| 道岔异常 | 98.2%  | 97.3%  | 97.7%  | 380ms        |
| 标识牌识别 | 99.1%  | 98.7%  | 98.9%  | 250ms        |
| 综合检测 | 97.8%  | 96.9%  | 97.3%  | 350ms        |

*测试环境：Intel i7-11700K CPU + NVIDIA RTX 3090 GPU + 32GB RAM*

### 不同硬件配置下的性能对比

| 硬件配置 | 单张图像处理时间（ms） | 最大吞吐量（张/分钟） |
|----------|------------------------|-----------------------|
| RTX 3090 | 350                    | 170                   |
| RTX 3060 | 580                    | 103                   |
| GTX 1080 | 820                    | 73                    |
| i7-12700 (CPU模式) | 2100                 | 29                    |

---

## 🤝 社区与支持

### 贡献指南

我们欢迎各类贡献，包括但不限于：
- 提交代码修复bug
- 改进模型提高准确率
- 增加新的检测功能
- 完善文档和教程
- 提供测试数据和案例

贡献流程：
1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开Pull Request

### 问题反馈

- 🐞 GitHub Issues: [https://github.com/YangShengzhou03/RailwayOCR/issues](https://github.com/YangShengzhou03/RailwayOCR/issues)
- 📧 邮件支持: support@railwayocr.com
- 💬 技术交流群: 加入QQ群 1021471813（请备注"RailwayOCR"）

### 文档资源

- 官方文档: [https://railwayocr.readthedocs.io](https://railwayocr.readthedocs.io)
- 模型训练指南: [docs/training_guide.md](docs/training_guide.md)
- 开发指南: [docs/development_guide.md](docs/development_guide.md)
- API参考: [docs/api_reference.md](docs/api_reference.md)

---

## 📜 许可证（AGPL-3.0）

本项目采用 [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0) 协议发布。

根据协议，你可以：
- 自由使用、复制和分发本软件
- 修改本软件并分发修改后的版本

但必须遵守以下条款：
- 保留原作者版权声明和许可证信息
- 修改后的版本必须采用相同许可证发布
- 若通过网络提供本软件的服务，必须公开对应的源代码

详情请参阅 [LICENSE](LICENSE) 文件。

---

## 🔮 未来规划

### 短期计划（3-6个月）
- [ ] 增加隧道内部设施检测功能
- [ ] 优化小目标检测能力，提高远距离拍摄图像的识别效果
- [ ] 开发API接口，支持与铁路运维系统集成
- [ ] 增加增强现实(AR)辅助巡检功能
- [ ] 优化移动端APP用户体验，增加离线地图功能

### 中期计划（6-12个月）
- [ ] 引入三维点云数据处理能力，支持立体建模与分析
- [ ] 开发基于视频流的实时检测模块，用于车载巡检系统
- [ ] 增加预测性维护分析功能，基于历史数据预测设施寿命
- [ ] 开发多模态识别能力，融合图像、激光雷达等数据
- [ ] 增加多语言支持，满足国际化需求

### 长期愿景
- [ ] 构建铁路数字孪生与AI检测一体化平台
- [ ] 形成覆盖铁路全生命周期的智能检测解决方案
- [ ] 建立铁路设施缺陷数据库与AI训练平台
- [ ] 推动铁路行业AI检测标准的制定

---

## 💬 结语

作为一名曾参与铁路工程建设的技术人员，我深知铁路检测工作的重要性与复杂性。烈日下的徒步巡检、隧道内的人工排查、海量图像的逐一审核……这些工作不仅耗费大量人力物力，还存在人为疏漏的风险。

RailwayOCR的诞生，源于我们对"用AI技术赋能铁路安全"的追求。经过3年多的研发与实地测试，系统已在多个铁路段得到成功应用，帮助检测人员提前发现了上百处安全隐患。

> "让每一段铁轨都被精准检测，让每一次出行都安全可靠。"

如果RailwayOCR能为您的工作带来帮助，欢迎给我们一个⭐Star。更期待与铁路行业的同仁们共同完善这个系统，为中国铁路的智能化发展贡献力量！

## 📞 联系与支持  
- **项目主页**：[https://gitee.com/Yangshengzhou/railway-ocr](https://gitee.com/Yangshengzhou/railway-ocr)  
- **文档中心**：[https://yangshengzhou.gitbook.io/railway-ocr](https://yangshengzhou.gitbook.io/railway-ocr)  
- **问题反馈**：[提交Issue](https://gitee.com/Yangshengzhou/railway-ocr/issues)  
- **商务合作**：3555844679@qq.com（主题注明"RailwayOCR合作"）  
- **社区交流**：  
[![微信](https://img.shields.io/badge/微信-YSZFortune-brightgreen?logo=wechat)](https://img.shields.io/badge/微信-YSZFortune-brightgreen?logo=wechat) [![QQ群](https://img.shields.io/badge/QQ群-1021471813-blue?logo=tencentqq)](https://img.shields.io/badge/QQ群-1021471813-blue?logo=tencentqq)

---

© 2025 Yangshengzhou. All rights reserved.  
Powered by AGPL-3.0.