"""
步骤⑦⑧⑨：生成模板 → 核价过滤 → 上传导入报名
"""
import os, time
from utils.log import log
from services.download_manager import DownloadManagerV2
from services.price_filter import filter_template
from config.settings import DOWNLOADS


def generate_template(page, context):
    """⑦ 生成并下载模板"""
    log("生成模板...")
    dl = DownloadManagerV2(context, page)
    filename = f"报名商品信息_{int(time.time())}.xlsx"
    template = dl.generate_template(
        trigger_fn=lambda: page.evaluate("""() => {
            const drawer = document.querySelector('[class*="Drawer"]');
            const btn = [...drawer.querySelectorAll('button')]
                .filter(b => b.innerText?.trim() === '生成模板');
            if (btn.length) btn[0].click();
        }"""),
        filename=filename,
    )
    if not template:
        log("下载失败，但浏览器保持存活。请检查后手动重试")
        return None
    size = os.path.getsize(template) // 1024
    log(f"下载完成: {os.path.basename(template)} ({size}KB)")
    return template


def run_price_filter(template_path):
    """⑧ 核价过滤"""
    log(f"核价过滤: {os.path.basename(template_path)}")
    filtered = filter_template(template_path)
    if not filtered:
        log("核价过滤失败")
        return None
    log(f"过滤完成: {os.path.basename(filtered)}")
    return filtered


def upload_and_submit(page, filtered_file):
    """⑨ 上传过滤文件 → 开始导入 → 确认报名"""
    log("上传过滤后的文件...")
    try:
        with page.expect_file_chooser(timeout=15000) as fc_info:
            page.evaluate("""() => {
                const drawer = document.querySelector('[class*="Drawer"]');
                const btn = [...drawer.querySelectorAll('button')].filter(b => b.innerText.trim() === '选择文件');
                if (btn.length) btn[0].click();
            }""")
        fc = fc_info.value
        fc.set_files(filtered_file)
        time.sleep(3)
    except Exception as e:
        log(f"上传失败: {e}")
        return False

    status = page.evaluate("""() => {
        const d = document.querySelector('[class*="Drawer"]');
        return d && d.innerText.includes('已过滤') ? 'FILE_FOUND' : 'FILE_NOT_VISIBLE';
    }""")
    log(f"文件状态: {status}")

    log("开始导入...")
    page.evaluate("""() => {
        const drawer = document.querySelector('[class*="Drawer"]');
        const btn = [...drawer.querySelectorAll('button')].filter(b => b.innerText.trim() === '开始导入');
        if (btn.length) btn[0].click();
    }""")
    time.sleep(3)

    log("确认并报名活动...")
    page.evaluate("""() => {
        const modal = document.querySelector('[data-testid="beast-core-modal"]');
        if (!modal) return;
        const btn = [...modal.querySelectorAll('button')].filter(b => b.innerText.trim() === '确认并报名活动');
        if (btn.length) btn[0].click();
    }""")
    time.sleep(2)

    log("==" * 25)
    log("报活动全流程完成！")
    log("==" * 25)
    return True
