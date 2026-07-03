import os
import re

base = "C:/workspace/agentDevBible"

def read_file(path):
    with open(path, 'r', encoding='utf-8') as fp:
        return fp.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as fp:
        fp.write(content)

# File 13: was chapter 16, now 13
f13 = os.path.join(base, "13_Agent开发指南_Harness与Loop工程化.md")
if os.path.exists(f13):
    content = read_file(f13)
    content = content.replace("# 第16章：Agent Harness 与 Loop 工程化", "# 第13章：Agent Harness 与 Loop 工程化")
    content = re.sub(r'^(## )\s*16\.', r'\1>13.', content, flags=re.MULTILINE)
    content = re.sub(r'^(### )\s*16\.', r'\1>13.', content, flags=re.MULTILINE)
    content = re.sub(r'\*\*定义\s+16\.', '**定义 13.', content)
    content = re.sub(r'\*\*定理\s+16\.', '**定理 13.', content)
    write_file(f13, content)
    print("Updated 13_ (was 16)")

# File 14: was chapter 13, now 14
f14 = os.path.join(base, "14_Agent开发指南_平台纵览_开发平台.md")
if os.path.exists(f14):
    content = read_file(f14)
    content = re.sub(r'^(## )\s*13\.', r'\1>14.', content, flags=re.MULTILINE)
    write_file(f14, content)
    print("Updated 14_ (was 13)")

# File 15 original: was chapter 14, now 15
f15 = os.path.join(base, "15_Agent开发指南_自我进化.md")
if os.path.exists(f15):
    content = read_file(f15)
    content = re.sub(r'\*\*定义\s+14\.', '**定义 15.', content)
    content = re.sub(r'\*\*定理\s+14\.', '**定理 15.', content)
    content = re.sub(r'^(## )\s*14\.', r'\1>15.', content, flags=re.MULTILINE)
    content = re.sub(r'^(### )\s*14\.', r'\1>15.', content, flags=re.MULTILINE)
    write_file(f15, content)
    print("Updated 15_ original (was 14)")

# File 15_core overview
f15c = os.path.join(base, "15_核心_Agent自我进化概述.md")
if os.path.exists(f15c):
    content = read_file(f15c)
    content = content.replace("第14章", "第15章")
    write_file(f15c, content)
    print("Updated 15_core overview")

# Files 15_appendices: 15_附录A through 15_附录J
appendices = [
    "附录A_OpenClaw八文件人格系统详解.md",
    "附录B_EvoMap基因进化协议与Q学习.md",
    "附录C_AI_Coding_Sandbox安全沙箱.md",
    "附录D_完整可运行代码实现指南.md",
    "附录E_进化系统架构与集群管理.md",
    "附录F_七层安全防护体系.md",
    "附录G_测试验证与质量保障.md",
    "附录H_企业部署_伦理与性能.md",
    "附录I_真实案例与延伸阅读.md",
    "附录J_致未来读者_时间胶囊.md",
]
for suffix in appendices:
    f = os.path.join(base, "15_" + suffix)
    if os.path.exists(f):
        content = read_file(f)
        content = re.sub(r'^(## )\s*14\.', r'\1>', content, flags=re.MULTILINE)
        content = re.sub(r'^(### )\s*14\.', r'\1>', content, flags=re.MULTILINE)
        content = content.replace("第14章", "第15章")
        write_file(f, content)
        print(f"  Updated 15_{suffix[:30]}")

# File 16: was 15 appendix A, now 16 appendix A
f16 = os.path.join(base, "16_Agent开发指南_附录A_术语解释.md")
if os.path.exists(f16):
    content = read_file(f16)
    content = content.replace("第15章", "第16章")
    write_file(f16, content)
    print("Updated 16_ terminology (was 15)")

# File 17: was 15 appendix B, now 17 appendix B
f17 = os.path.join(base, "17_Agent开发指南_附录B_初级程序员必读.md")
if os.path.exists(f17):
    content = read_file(f17)
    content = content.replace("第15章", "前面的章节")
    write_file(f17, content)
    print("Updated 17_ primary programmer (was 15)")

print("\nAll updates done.")
