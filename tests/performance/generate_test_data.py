"""生成 5000 条模拟文档数据用于扩展性验证"""
import random
from pathlib import Path

TEMPLATES = [
    "关于{topic}的通知", "{year}年度{topic}工作总结", "{topic}调研报告",
    "关于{topic}的请示", "{topic}实施方案", "{topic}会议纪要",
]
TOPICS = ["信息化建设", "人才培养", "安全生产", "财务管理", "党建", "创新驱动", "营商环境", "乡村振兴"]
YEARS = ["2024", "2025", "2026"]


def generate_documents(count: int = 5000, output_dir: str = "./data/perf_test"):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        topic = random.choice(TOPICS)
        year = random.choice(YEARS)
        title = random.choice(TEMPLATES).format(topic=topic, year=year)
        content = f"{title}\n\n" + "\n".join(
            f"第{j+1}段内容：关于{topic}的第{j+1}个方面的详细阐述。" * 3
            for j in range(random.randint(3, 10))
        )
        (out / f"doc_{i:05d}.txt").write_text(content, encoding="utf-8")
    print(f"已生成 {count} 条文档到 {output_dir}")


if __name__ == "__main__":
    generate_documents()
