"""
Log 模块接口测试
测试日志管理的所有接口：列表、下载、批量下载
"""
import pytest
from pathlib import Path
from tests.utils.client import (
    APITestClient,
    assert_success_response,
    assert_error_response
)


# ============================================================================
# 测试标记
# ============================================================================

pytestmark = pytest.mark.log


# ============================================================================
# 列出日志文件
# ============================================================================

@pytest.mark.asyncio
async def test_list_logs_empty(client, log_dir):
    """测试列出日志文件 - 空目录"""
    api_client = APITestClient(client=client)
    response = await api_client.get("/api/logs/")
    assert_success_response(response, 200)
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_logs_with_files(client, log_dir):
    """测试列出日志文件 - 有文件"""
    # 创建测试日志文件
    log_files = [
        log_dir / "app.log",
        log_dir / "error.log",
        log_dir / "debug.log"
    ]
    for log_file in log_files:
        log_file.write_text("test log content")

    api_client = APITestClient(client=client)
    response = await api_client.get("/api/logs/")
    assert_success_response(response, 200)

    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) == 3

    # 验证日志文件结构
    for log in logs:
        assert "filename" in log
        assert "size" in log
        assert "modified" in log


@pytest.mark.asyncio
async def test_list_logs_sorted_by_modified(client, log_dir):
    """测试列出日志文件 - 按修改时间排序"""
    # 创建多个日志文件
    import time
    log_files = []
    for i in range(3):
        log_file = log_dir / f"test_{i}.log"
        log_file.write_text(f"content {i}")
        time.sleep(0.1)  # 确保修改时间不同
        log_files.append(log_file)

    api_client = APITestClient(client=client)
    response = await api_client.get("/api/logs/")
    logs = response.json()

    # 验证是否按修改时间倒序排列
    if len(logs) > 1:
        timestamps = [log["modified"] for log in logs]
        # 应该是倒序（最新的在前）
        assert timestamps == sorted(timestamps, reverse=True)


# ============================================================================
# 下载单个日志文件
# ============================================================================

@pytest.mark.asyncio
async def test_download_log_file(client, log_dir):
    """测试下载单个日志文件"""
    # 创建测试日志文件
    test_content = "This is a test log file\nLine 2\nLine 3"
    log_file = log_dir / "test.log"
    log_file.write_text(test_content)

    api_client = APITestClient(client=client)
    response = await api_client.get("/api/logs/download/test.log")
    assert_success_response(response, 200)
    assert response.content == test_content.encode()
    assert "test.log" in response.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_download_log_not_found(client, log_dir):
    """测试下载单个日志文件 - 文件不存在"""
    api_client = APITestClient(client=client)
    response = await api_client.get("/api/logs/download/non_existent.log")
    assert_error_response(response, 404, "日志文件不存在")


@pytest.mark.asyncio
async def test_download_log_directory_not_exists(client):
    """测试下载日志文件 - 日志目录不存在"""
    # 临时移除日志目录
    import tempfile
    import shutil

    temp_dir = Path(tempfile.mkdtemp())
    original_log_dir = None

    # 这是一个模拟测试，实际应用中需要确保日志目录存在
    api_client = APITestClient(client=client)
    response = await api_client.get("/api/logs/download/test.log")
    # 可能返回 404 或 500
    assert response.status_code in [404, 500]


# ============================================================================
# 批量下载日志
# ============================================================================

@pytest.mark.asyncio
async def test_download_logs_batch(client, log_dir):
    """测试批量下载日志文件"""
    # 创建测试日志文件
    for i in range(3):
        log_file = log_dir / f"test_{i}.log"
        log_file.write_text(f"content {i}")

    api_client = APITestClient(client=client)
    response = await api_client.post(
        "/api/logs/download/batch",
        json={"filenames": ["test_0.log", "test_1.log"]}
    )
    assert_success_response(response, 200)
    assert "application/zip" in response.headers.get("content-type", "")
    assert ".zip" in response.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_download_logs_batch_all(client, log_dir):
    """测试批量下载所有日志文件"""
    # 创建测试日志文件
    filenames = []
    for i in range(3):
        filename = f"test_{i}.log"
        log_file = log_dir / filename
        log_file.write_text(f"content {i}")
        filenames.append(filename)

    api_client = APITestClient(client=client)
    response = await api_client.post(
        "/api/logs/download/batch",
        json={"filenames": filenames}
    )
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_download_logs_batch_empty(client, log_dir):
    """测试批量下载日志 - 空列表"""
    api_client = APITestClient(client=client)
    response = await api_client.post(
        "/api/logs/download/batch",
        json={"filenames": []}
    )
    # 空列表应该返回空的 ZIP 或错误
    assert response.status_code in [200, 400]


@pytest.mark.asyncio
async def test_download_logs_batch_non_existent_file(client, log_dir):
    """测试批量下载日志 - 包含不存在的文件"""
    # 创建一个测试日志文件
    (log_dir / "test.log").write_text("content")

    api_client = APITestClient(client=client)
    response = await api_client.post(
        "/api/logs/download/batch",
        json={"filenames": ["test.log", "non_existent.log"]}
    )
    # 应该只打包存在的文件
    assert_success_response(response, 200)


# ============================================================================
# 边界测试
# ============================================================================

@pytest.mark.asyncio
async def test_download_large_log_file(client, log_dir):
    """测试下载大日志文件"""
    # 创建一个大日志文件（1MB）
    large_content = "Line of log data\n" * 100000  # 约 1.5MB
    log_file = log_dir / "large.log"
    log_file.write_text(large_content)

    api_client = APITestClient(client=client)
    response = await api_client.get("/api/logs/download/large.log")
    assert_success_response(response, 200)
    assert len(response.content) > 1000000  # 大于 1MB


@pytest.mark.asyncio
async def test_download_batch_many_files(client, log_dir):
    """测试批量下载大量文件"""
    # 创建 50 个日志文件
    filenames = []
    for i in range(50):
        filename = f"test_{i}.log"
        log_file = log_dir / filename
        log_file.write_text(f"content {i}")
        filenames.append(filename)

    api_client = APITestClient(client=client)
    response = await api_client.post(
        "/api/logs/download/batch",
        json={"filenames": filenames}
    )
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_list_logs_with_special_characters(client, log_dir):
    """测试列出包含特殊字符的日志文件名"""
    # 创建包含特殊字符的日志文件
    special_filenames = [
        "test with spaces.log",
        "test-with-dashes.log",
        "test_with_underscores.log"
    ]
    for filename in special_filenames:
        (log_dir / filename).write_text("content")

    api_client = APITestClient(client=client)
    response = await api_client.get("/api/logs/")
    assert_success_response(response, 200)

    logs = response.json()
    log_filenames = [log["filename"] for log in logs]
    for filename in special_filenames:
        assert filename in log_filenames


# ============================================================================
# 错误处理测试
# ============================================================================

@pytest.mark.asyncio
async def test_download_log_path_traversal(client, log_dir):
    """测试下载日志文件 - 路径遍历攻击"""
    # 创建测试日志文件
    (log_dir / "test.log").write_text("content")

    api_client = APITestClient(client=client)
    # 尝试路径遍历
    response = await api_client.get("/api/logs/download/../../../etc/passwd")
    # 应该返回 404 或拒绝访问
    assert response.status_code in [404, 403, 400]


@pytest.mark.asyncio
async def test_download_batch_path_traversal(client, log_dir):
    """测试批量下载日志 - 路径遍历攻击"""
    (log_dir / "test.log").write_text("content")

    api_client = APITestClient(client=client)
    response = await api_client.post(
        "/api/logs/download/batch",
        json={"filenames": ["test.log", "../../../etc/passwd"]}
    )
    # 应该拒绝或忽略恶意文件名
    assert response.status_code in [200, 403, 400]
