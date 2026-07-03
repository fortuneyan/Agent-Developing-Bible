import os, re

base = "C:/workspace/agentDevBible"

def fix_file(path, old_chap, new_chap):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix title
    content = content.replace(f"# 第{old_chap}章", f"# 第{new_chap}章")
    
    # Fix section headers: ## OLD.CHAPNUM -> ## NEW.CHAPNUM
    # Headers like "## 16.1 ..." or "### 16.1.1 ..."
    content = re.sub(
        r'^(#{2,4})\s+' + str(old_chap) + r'\.',
        r'\1 ' + str(new_chap) + '.',
        content,
        flags=re.MULTILINE
    )
    
    # Fix definitions/theorems: **定义 OLD. -> **定义 NEW.
    content = re.sub(r'\*\*定义\s+' + str(old_chap) + r'\.', '**定义 ' + str(new_chap) + '.', content)
    content = re.sub(r'\*\*定理\s+' + str(old_chap) + r'\.', '**定理 ' + str(new_chap) + '.', content)
    
    # Fix "第OLD章" references
    content = content.replace(f"第{old_chap}章", f"第{new_chap}章")
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  Fixed {os.path.basename(path)}")

# Fix 13_ (was 16)
fix_file(os.path.join(base, "13_Agent开发指南_Harness与Loop工程化.md"), 16, 13)

# Fix 14_ (was 13)
fix_file(os.path.join(base, "14_Agent开发指南_平台纵览_开发平台.md"), 13, 14)

# Fix 15_ original (was 14)
fix_file(os.path.join(base, "15_Agent开发指南_自我进化.md"), 14, 15)

# Fix 15_ appendices (were extracted from ch14, have 14.x headers)
for suffix in ["附录A_OpenClaw八文件人格系统详解.md", "附录B_EvoMap基因进化协议与Q学习.md",
              "附录C_AI_Coding_Sandbox安全沙箱.md", "附录D_完整可运行代码实现指南.md",
              "附录E_进化系统架构与集群管理.md", "附录F_七层安全防护体系.md",
              "附录G_测试验证与质量保障.md", "附录H_企业部署_伦理与性能.md",
              "附录I_真实案例与延伸阅读.md", "附录J_致未来读者_时间胶囊.md"]:
    fix_file(os.path.join(base, "15_" + suffix), 14, 15)

# Also fix the >13. issue in 13_ file (stray > from previous bad regex)
f13 = os.path.join(base, "13_Agent开发指南_Harness与Loop工程化.md")
with open(f13, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace(">13.", "13.")
with open(f13, 'w', encoding='utf-8') as f:
    f.write(content)
print("  Also fixed stray > in 13_ file")

print("\nAll fixed.")
