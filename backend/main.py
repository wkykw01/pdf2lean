from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import PyPDF2
import io
import os
import subprocess
import tempfile
import shutil
import httpx
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

AGENT_SERVER_URL = os.getenv("AGENT_SERVER_URL", "http://localhost:8000")

app = FastAPI()

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Chapter(BaseModel):
    id: str
    title: str
    content: str
    page_start: int
    page_end: int

class TheoremRequest(BaseModel):
    chapters: List[Chapter]
    prompt: str

class LaTeXCompileRequest(BaseModel):
    latex_content: str
    filename: Optional[str] = "document"

@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """上传PDF并提取章节"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持PDF文件")

    try:
        # 读取PDF
        pdf_bytes = await file.read()
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        # 提取文本
        full_text = ""
        for page in pdf_reader.pages:
            full_text += page.extract_text() + "\n"

        # 简单章节识别（基于常见标题模式）
        chapters = extract_chapters(full_text, len(pdf_reader.pages))

        return {
            "success": True,
            "filename": file.filename,
            "total_pages": len(pdf_reader.pages),
            "chapters": chapters
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF处理失败: {str(e)}")

def extract_chapters(text: str, total_pages: int) -> List[dict]:
    """提取章节（简单实现，后续可用LLM优化）"""
    lines = text.split('\n')
    chapters = []
    current_chapter = None
    chapter_id = 0

    for i, line in enumerate(lines):
        line = line.strip()
        # 识别章节标题（第X章、Chapter、定理、引理等）
        if any(keyword in line for keyword in ['第', '章', 'Chapter', '定理', '引理', 'Theorem', 'Lemma']):
            if len(line) < 50 and len(line) > 3:  # 标题长度合理
                if current_chapter:
                    chapters.append(current_chapter)

                chapter_id += 1
                current_chapter = {
                    "id": f"chapter_{chapter_id}",
                    "title": line,
                    "content": "",
                    "page_start": int(i / len(lines) * total_pages) + 1,
                    "page_end": 0
                }
        elif current_chapter:
            current_chapter["content"] += line + "\n"

    # 添加最后一章
    if current_chapter:
        current_chapter["page_end"] = total_pages
        chapters.append(current_chapter)

    # 如果没识别到章节，整个文档作为一章
    if not chapters:
        chapters = [{
            "id": "chapter_1",
            "title": "全文",
            "content": text,
            "page_start": 1,
            "page_end": total_pages
        }]

    return chapters

@app.post("/api/select-theorem")
async def select_theorem(request: TheoremRequest):
    """根据提示词选择最重要的定理，返回三级节点树"""
    # TODO: 接入 LLM 分析，当前返回 mock 数据
    theorem_tree = {
        "id": "theorem_1",
        "level": 1,
        "title": "每个非零复数恰有 n 个 n 次方根",
        "source_text": "设 $z \\in \\mathbb{C}^*$，则方程 $w^n = z$ 恰有 n 个不同的复数解。",
        "lean_code": "theorem complex_nth_roots (z : ℂ) (n : ℕ) (hn : n ≠ 0) (hz : z ≠ 0) :\n  ∃! (roots : Finset ℂ), roots.card = n ∧ ∀ w ∈ roots, w ^ n = z",
        "lean_verified": False,
        "children": [
            {
                "id": "lemma_2_1",
                "level": 2,
                "title": "引理 2.1: 复数的极坐标表示",
                "source_text": "任意非零复数 $z$ 可唯一表示为 $z = r e^{i\\theta}$，其中 $r = |z| > 0$，$\\theta \\in [0, 2\\pi)$。",
                "lean_code": "lemma complex_polar_form (z : ℂ) (hz : z ≠ 0) :\n  ∃ (r : ℝ) (θ : ℝ), r > 0 ∧ z = r * Complex.exp (θ * Complex.I)",
                "lean_verified": False,
                "children": [
                    {
                        "id": "prop_3_1",
                        "level": 3,
                        "title": "命题 3.1: 欧拉公式",
                        "source_text": "$e^{i\\theta} = \\cos\\theta + i\\sin\\theta$",
                        "lean_code": "theorem euler_formula (θ : ℝ) :\n  Complex.exp (θ * Complex.I) = ↑(Real.cos θ) + ↑(Real.sin θ) * Complex.I",
                        "lean_verified": False,
                        "children": []
                    },
                    {
                        "id": "prop_3_2",
                        "level": 3,
                        "title": "命题 3.2: 复数模长的乘法性质",
                        "source_text": "$|z_1 \\cdot z_2| = |z_1| \\cdot |z_2|$",
                        "lean_code": "theorem complex_abs_mul (z₁ z₂ : ℂ) :\n  Complex.abs (z₁ * z₂) = Complex.abs z₁ * Complex.abs z₂",
                        "lean_verified": False,
                        "children": []
                    }
                ]
            },
            {
                "id": "lemma_2_2",
                "level": 2,
                "title": "引理 2.2: n 次单位根的存在性",
                "source_text": "方程 $w^n = 1$ 恰有 n 个解，即 $\\omega_k = e^{2\\pi i k / n}$，其中 $k = 0, 1, \\ldots, n-1$。",
                "lean_code": "lemma unity_roots (n : ℕ) (hn : n ≠ 0) :\n  ∃ (roots : Finset ℂ), roots.card = n ∧ ∀ w ∈ roots, w ^ n = 1",
                "lean_verified": False,
                "children": [
                    {
                        "id": "prop_3_4",
                        "level": 3,
                        "title": "命题 3.4: 指数函数的周期性",
                        "source_text": "$e^{i(\\theta + 2\\pi k)} = e^{i\\theta}$ 对所有整数 $k$ 成立",
                        "lean_code": "theorem exp_periodic (θ : ℝ) (k : ℤ) :\n  Complex.exp ((θ + 2 * Real.pi * k) * Complex.I) = Complex.exp (θ * Complex.I)",
                        "lean_verified": False,
                        "children": []
                    },
                    {
                        "id": "prop_3_5",
                        "level": 3,
                        "title": "命题 3.5: 有限集合的基数唯一性",
                        "source_text": "若两个有限集合之间存在双射，则它们的基数相等",
                        "lean_code": "theorem finset_card_bij {α β : Type*} (s : Finset α) (t : Finset β)\n  (f : α → β) (hf : Function.Bijective f) : s.card = t.card",
                        "lean_verified": False,
                        "children": []
                    }
                ]
            },
            {
                "id": "lemma_2_3",
                "level": 2,
                "title": "引理 2.3: n 次方根的构造公式",
                "source_text": "若 $z = r e^{i\\theta}$，则 $w^n = z$ 的解为 $w_k = \\sqrt[n]{r} \\cdot e^{i(\\theta + 2\\pi k)/n}$，$k = 0, \\ldots, n-1$。",
                "lean_code": "lemma nth_root_formula (z : ℂ) (n : ℕ) (r : ℝ) (θ : ℝ)\n  (hz : z = r * Complex.exp (θ * Complex.I)) (hn : n ≠ 0) :\n  ∀ k : Fin n, (r ^ (1 / (n : ℝ)) * Complex.exp ((θ + 2 * Real.pi * k) / n * Complex.I)) ^ n = z",
                "lean_verified": False,
                "children": [
                    {
                        "id": "prop_3_3",
                        "level": 3,
                        "title": "命题 3.3: 复数幅角的加法性质",
                        "source_text": "$\\arg(z_1 \\cdot z_2) = \\arg(z_1) + \\arg(z_2) \\pmod{2\\pi}$",
                        "lean_code": "theorem complex_arg_mul (z₁ z₂ : ℂ) (hz₁ : z₁ ≠ 0) (hz₂ : z₂ ≠ 0) :\n  Complex.arg (z₁ * z₂) = (Complex.arg z₁ + Complex.arg z₂) % (2 * Real.pi)",
                        "lean_verified": False,
                        "children": []
                    }
                ]
            }
        ]
    }

    return {
        "success": True,
        "theorem_tree": theorem_tree,
        "prompt": request.prompt
    }

@app.get("/")
async def root():
    return {"message": "形式化证明系统 API"}

@app.post("/api/compile-latex")
async def compile_latex(request: LaTeXCompileRequest):
    """编译 LaTeX 代码，返回 PDF 或错误信息"""
    temp_dir = None
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        tex_file = Path(temp_dir) / f"{request.filename}.tex"
        pdf_file = Path(temp_dir) / f"{request.filename}.pdf"
        log_file = Path(temp_dir) / f"{request.filename}.log"

        # 写入 LaTeX 文件
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(request.latex_content)

        # 调用 pdflatex 编译
        result = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', '-output-directory', temp_dir, str(tex_file)],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 检查是否生成了 PDF
        if pdf_file.exists():
            # 编译成功，返回 PDF 文件路径
            # 将 PDF 复制到持久化目录
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            final_pdf = output_dir / f"{request.filename}.pdf"
            shutil.copy(pdf_file, final_pdf)

            return {
                "success": True,
                "message": "LaTeX 编译成功",
                "pdf_path": str(final_pdf),
                "log": result.stdout
            }
        else:
            # 编译失败，读取日志
            error_log = ""
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    error_log = f.read()

            # 调用 agent 服务获取修复建议
            traces = [result.stdout, result.stderr]
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    fix_response = await client.post(
                        f"{AGENT_SERVER_URL}/latex/fix",
                        json={
                            "latex_content": request.latex_content,
                            "error_log": error_log or result.stderr,
                            "traces": traces
                        }
                    )
                    if fix_response.status_code == 200:
                        fix_data = fix_response.json()
                        return {
                            "success": False,
                            "message": "LaTeX 编译失败",
                            "error_log": error_log or result.stderr,
                            "analysis": fix_data.get("analysis", ""),
                            "fixed_latex": fix_data.get("fixed_latex", ""),
                            "traces": traces
                        }
            except Exception as agent_error:
                # Agent 服务调用失败，返回基础错误信息
                pass

            return {
                "success": False,
                "message": "LaTeX 编译失败",
                "error_log": error_log or result.stderr,
                "analysis": "Agent 服务暂时不可用",
                "traces": traces
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "LaTeX 编译超时（超过30秒）",
            "error_log": "编译过程超时",
            "fix_suggestions": ["检查是否有无限循环或过大的文档", "尝试简化 LaTeX 代码"]
        }

    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="未找到 pdflatex 命令，请确保已安装 TeX Live 或 MiKTeX"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"编译过程出错: {str(e)}")

    finally:
        # 清理临时目录
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.get("/api/download-pdf/{filename}")
async def download_pdf(filename: str):
    """下载编译好的 PDF 文件"""
    pdf_path = Path("output") / f"{filename}.pdf"

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF 文件不存在")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"{filename}.pdf"
    )


@app.post("/api/pdf-to-latex")
async def pdf_to_latex(file: UploadFile = File(...)):
    """上传 PDF，提取文本后调用 agent 服务转换为 LaTeX"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持PDF文件")

    try:
        pdf_bytes = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))

        full_text = ""
        for page in pdf_reader.pages:
            full_text += page.extract_text() + "\n"

        filename = file.filename.replace('.pdf', '')

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{AGENT_SERVER_URL}/latex/convert",
                json={"pdf_text": full_text, "filename": filename}
            )
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Agent 服务调用失败")

            data = response.json()
            return {
                "success": True,
                "filename": filename,
                "latex_content": data.get("latex_content", ""),
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")