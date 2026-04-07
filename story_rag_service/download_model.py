"""
下载HuggingFace模型到本地
在有网络的环境(本地Windows)运行此脚本,然后将模型文件上传到服务器
"""

import os
from sentence_transformers import SentenceTransformer

def download_model():
    """下载embedding模型"""
    
    model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    save_path = "./data/huggingface_cache/models"
    
    print(f"📥 开始下载模型: {model_name}")
    print(f"💾 保存位置: {save_path}")
    
    # 创建目录
    os.makedirs(save_path, exist_ok=True)
    
    try:
        # 下载模型
        print("⏳ 正在下载模型文件(约470MB)...")
        model = SentenceTransformer(model_name)
        
        # 保存到本地
        model_save_path = os.path.join(save_path, "paraphrase-multilingual-MiniLM-L12-v2")
        model.save(model_save_path)
        
        print(f"\n✅ 模型下载成功!")
        print(f"📂 模型位置: {os.path.abspath(model_save_path)}")
        print(f"\n📤 下一步:")
        print(f"   1. 将整个 'data/huggingface_cache' 文件夹打包")
        print(f"   2. 上传到服务器: /www/wwwroot/story_rag_service/data/")
        print(f"   3. 在服务器上解压,确保路径为: /www/wwwroot/story_rag_service/data/huggingface_cache/")
        
        # 测试加载
        print(f"\n🧪 测试加载模型...")
        test_model = SentenceTransformer(model_save_path)
        test_embedding = test_model.encode("测试文本")
        print(f"✅ 模型测试成功! 向量维度: {len(test_embedding)}")
        
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        print(f"\n💡 如果下载失败,可以:")
        print(f"   1. 检查网络连接")
        print(f"   2. 设置代理: export HTTP_PROXY=http://your-proxy:port")
        print(f"   3. 或手动从 https://huggingface.co/{model_name} 下载")

if __name__ == "__main__":
    download_model()
