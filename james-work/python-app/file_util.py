""" 文件处理模块
"""
import os
import sys
from pathlib import Path
import hashlib
import re
import shutil
import subprocess
import random
import time
import traceback
from typing import List, Optional, Union
import io
from PyPDF2 import PdfReader
import pandas as pd
import requests
from datetime import datetime

# Optional S3 support - only import if available
try:
    sys.path.insert(0, '/home/jiangqian/Documents/_AllDocMap/02_Project/git_dir/xinghe-main/xinghe')
    from xinghe.s3 import *
    S3_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    S3_AVAILABLE = False

# # 配置基础日志（生产环境可接入Sentry等监控系统）
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('file_util.log'),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)


class FileUtil:
    """ 文件操作工具类

    封装文件遍历、路径处理等高频操作，强化异常处理与健壮性。
    """

    @staticmethod
    def get_file_hash(file_path, algorithm='sha256', buffer_size=65536, client=None, need_ex_info = False, need_pdf_bytes = False, retry_num = 0):
        """
        通用文件哈希计算函数，支持：
        - 本地文件路径（如 `/data/file.txt`）
        - S3 路径（如 `s3://bucket/path/to/file.txt`）
        
        参数:
            file_path (str): 文件路径（本地或S3）
            algorithm (str): 哈希算法（默认 'sha256'）
            buffer_size (int): 缓冲区大小（字节）
            client (boto3.client): 可复用的 S3 客户端（可选）
        
        返回:
            str: 文件的十六进制哈希值
        
        示例:
            # 本地文件
            hash_local = get_file_hash('/data/file.txt')
            
            # S3 文件（自动处理 s3:// 路径）
            hash_s3 = get_file_hash('s3://my-bucket/path/to/file.txt')
        """
        hash_obj = hashlib.new(algorithm)
        ex_info = []
        stream = None
        pdf_bytes = b''
        file_tag = None
        try:
            if file_path.startswith('s3://'):
                client = client or get_s3_client(file_path)
                file_obj = get_s3_object(file_path, client)
                stream = file_obj['Body']
                content_length = file_obj['ContentLength']
            else:
                stream = open(file_path, 'rb')
                content_length = os.path.getsize(file_path)

            if need_ex_info:
                chunk_0 = stream.read(buffer_size)
                file_format, mime = guess_ext_from_bytes(chunk_0, return_mime = True, file_path = file_path)
                hash_obj.update(chunk_0)
            
                ex_info = [content_length, file_format, mime]
                file_tag = get_file_tag(file_path, file_format, content_length)
                
                if need_pdf_bytes and file_tag == 'pdf_normal_size':
                    pdf_bytes = chunk_0
                
            while chunk := stream.read(buffer_size):
                hash_obj.update(chunk)
                if need_pdf_bytes and file_tag == 'pdf_normal_size':
                    pdf_bytes += chunk
                    
            if need_pdf_bytes:
                ex_info.extend( [pdf_bytes, file_tag] )
                
            hash_value = hash_obj.hexdigest()
        except Exception as e:
            err_str = str(e)
            not_exist_msg = ['(NoSuchKey)', '(NoSuchBucket)']
            if any(msg in err_str for msg in not_exist_msg):
                return None
            elif '(SlowDown)' in err_str:
                if retry_num < 4:
                    delay = 1 * (2 ** retry_num) + random.uniform(0, 1)
                    time.sleep(delay)
                    return get_file_hash(file_path, client=client, need_ex_info = need_ex_info, need_pdf_bytes = need_pdf_bytes, retry_num = retry_num + 1)
                else:
                    raise RuntimeError(f'计算文件哈希失败 (SlowDown): {ct(file_path, "red")}  \n{ traceback.format_exc() }')
                    # return None
            else:
                raise RuntimeError(f'计算文件哈希失败: {ct(file_path, "red")}  \n{ traceback.format_exc() }')
        finally:
            if stream:
                stream.close()
        return (hash_value, *ex_info) if need_ex_info else hash_value



    @staticmethod
    def read_large_file(input_path):
        """
        按行迭代读取大文本文件，避免内存溢出（OOM）
        :param input_path: 文件路径
        :yield: 逐行返回文件内容（自动处理换行符，可按需调整）
        """
        # 推荐使用 encoding 指定编码（如 utf-8），避免乱码
        with open(input_path, mode='r', encoding='utf-8') as f:
            # 方式1：直接迭代文件对象（最简洁、高效，Python 推荐写法）
            for line in f:
                # 可选：去除行尾换行符/空白符（根据业务需求决定）
                # line = line.rstrip('\n')  # 仅去换行符
                # line = line.strip()       # 去所有首尾空白（含换行、空格、制表符）
                yield line  # 生成器（迭代器）返回每行内容

    @staticmethod
    def make_parent_dir_if_missing(file_name):
        """如果文件目录不存在，则创建目录"""
        dir_name = os.path.dirname(file_name)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"目录 {dir_name} 被创建.")

    @staticmethod
    def make_file_name_with_timestamp(dir, suffix="log", filename=None):
        """function docstring here"""
        filename = os.path.basename(__file__).split(
            '.')[0] if filename is None else filename
        basename = os.path.basename(filename)
        filename = os.path.splitext(basename)[0]
        # print(f"filename = {filename}")

        current_file_name = filename
        now_time = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")
        generated_file_name = f"{dir}/{current_file_name}_{now_time}.{suffix}"
        # print(f"generated_file_name = {generated_file_name}")

        return generated_file_name


    @staticmethod
    def download_pdf(pdf_url: str, output_path: str) -> bool:
        """
        下载指定 PDF URL 并保存到 output_path
        
        :param pdf_url: PDF 文件的下载链接（必须是能直接返回 PDF 文件的二进制流的 URL）
        :param output_path: 保存的本地路径，如：./downloads/announcement.pdf
        :return: 是否下载成功
        """
        try:
            # 发送 GET 请求，stream=True 用于下载大文件
            response = requests.get(pdf_url, stream=True)
            response.raise_for_status()  # 检查请求是否成功

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 以二进制写入模式保存文件
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ PDF 已成功下载到：{output_path}")
            return 0
        except Exception as e:
            print(f"❌ 下载失败：{e}")
            return 1

    @staticmethod
    def delete_pdf_files_in_dir(directory) -> None:
        """
        删除指定目录下所有以 .pdf 结尾的文件
        :param directory: 目标目录路径
        """
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.pdf'):
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                        print(f"已删除文件: {file_path}")
                    except FileNotFoundError:
                        print(f"文件未找到: {file_path}")
                    except PermissionError:
                        print(f"权限不足，无法删除文件: {file_path}")
                    except Exception as e:
                        print(f"删除文件时发生错误: {e}")

    @staticmethod
    def move_directory_contents(src_dir, dest_dir):
        """
        将源目录内容移动到目标目录，并在完成后删除源目录并重建同名空目录
        :param src_dir: 源目录路径
        :param dest_dir: 目标目录路径
        :return: 操作结果状态 (True/False)
        """
        try:
            # 验证源目录存在性
            if not os.path.exists(src_dir):
                raise FileNotFoundError(f"源目录不存在: {src_dir}")

            # 创建目标目录结构
            os.makedirs(dest_dir, exist_ok=True)

            # 遍历移动所有内容
            for root, dirs, files in os.walk(src_dir, topdown=False):
                relative_path = os.path.relpath(root, src_dir)
                dest_path = os.path.join(dest_dir, relative_path)

                # 移动文件
                for file in files:
                    src_file = os.path.join(root, file)
                    dest_file = os.path.join(dest_path, file)
                    shutil.move(src_file, dest_file)

                # 移动空目录（处理嵌套目录结构）
                for dir in dirs:
                    src_subdir = os.path.join(root, dir)
                    dest_subdir = os.path.join(dest_path, dir)
                    if os.path.exists(dest_subdir):
                        os.rmdir(dest_subdir)  # 清空目标子目录
                    shutil.move(src_subdir, dest_subdir)

            # 删除并重建源目录
            shutil.rmtree(src_dir)
            os.makedirs(src_dir, exist_ok=True)  # 创建同名空目录

            print(f"成功迁移并重建目录: {src_dir} -> {dest_dir}")
            return True

        except shutil.Error as e:
            print(f"文件冲突错误: {e}")
        except PermissionError as e:
            print(f"权限错误: {e} (建议检查文件权限或关闭占用程序)")
        except Exception as e:
            print(f"未知错误: {e}")
        return False

    @staticmethod
    def read_md_files(path: str) -> str:
        """
        读取指定路径下所有.md文件内容并合并为字符串
        
        参数：
        path (str): 目标目录路径
        
        返回：
        str: 合并后的Markdown内容字符串
        """
        merged_content = []
        
        # 遍历目录及其子目录
        for root, dirs, files in os.walk(path):
            # 过滤.md文件并按文件名排序
            md_files = sorted([f for f in files if f.lower().endswith('.md')])
            
            for file_name in md_files:
                file_path = os.path.join(root, file_name)
                try:
                    # 读取文件内容（处理编码问题）
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        merged_content.append(f"## {file_name}\n\n{content}\n\n")
                except Exception as e:
                    print(f"读取文件失败: {file_path} - {str(e)}")
        
        # 使用两个换行符分隔不同文件内容
        return '\n\n'.join(merged_content)

    @staticmethod
    def extract_pdf_content_with_mineru(pdf_path: str, output_path:str) -> pd.DataFrame:
        try:
            if not pdf_path.endswith('.pdf'):
                return 1
        
            # command = f"/opt/anaconda3/envs/venv_conda_py311/bin/mineru -p {os.path.dirname(pdf_path)} -o {output_path} --cache-dir=/dev/null --no-model-cache"
            # print(f"command: {command}")
            # result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            # print(result.stdout)
            
            pdf_file_name = os.path.basename(pdf_path).replace(".pdf", "")
            md_file_path = FileUtil.query_file_names_from_folder(file_path=f"{output_path}/{pdf_file_name}/auto", file_suffix="md")[0]
            if(len(md_file_path) == 0):
                return 1
            
            print(f"md_file_path: {md_file_path}")
            with open(md_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_md = f.read()

            md_file_path = f"{output_path}/{pdf_file_name}"
            df = pd.DataFrame([[{pdf_file_name}, {md_file_path}, file_md]], columns=['file_name', 'file_path', 'file_md'])
            return df

        except Exception as e:
            print(f"Error: {e.stderr}")

    @staticmethod
    def copy_file_to_path(
        src: str,
        dst: Union[str, Path],
        overwrite: bool = False,
        preserve_metadata: bool = True
    ) -> None:
        """
        增强版文件复制工具，支持路径自动处理和元数据保留

        Args:
            src (str): 源文件绝对/相对路径
            dst (Union[str, Path]): 目标路径（支持目录或文件名）
            overwrite (bool): 是否覆盖已存在文件（默认False）
            preserve_metadata (bool): 是否保留元数据（默认True）

        Raises:
            FileNotFoundError: 源文件不存在
            PermissionError: 权限不足
            ValueError: 目标路径无效
        """
        # 转换为Path对象
        src_path = Path(src)
        dst_path = Path(dst)

        # 验证源文件存在性
        if not src_path.is_file():
            raise FileNotFoundError(f"源文件不存在: {src}")

        # 处理目标路径
        if dst_path.is_dir():
            dst_path = dst_path / src_path.name
        elif dst_path.suffix == '':
            raise ValueError("目标路径无效，需指定文件名或目录")

        # 覆盖检查
        if dst_path.exists() and not overwrite:
            raise FileExistsError(f"目标文件已存在: {dst_path}")

        try:
            # 执行复制操作
            if preserve_metadata:
                shutil.copy2(src_path, dst_path)
            else:
                shutil.copy(src_path, dst_path)
            print(f"文件成功复制到: {dst_path}")

        except PermissionError as e:
            raise PermissionError(f"无权限操作文件: {e.filename}") from e
        except OSError as e:
            raise RuntimeError(f"文件操作失败: {str(e)}") from e


    @staticmethod
    def query_file_names_from_folder(file_path: str, file_suffix: str = 'pdf') -> List[str]:
        """
        递归遍历指定目录，获取所有符合指定文件后缀的文件绝对路径列表。
    
        Args:
            file_path (str): 待遍历的根目录路径。
            file_suffix (str, optional): 目标文件后缀，默认为'pdf'，支持大小写不敏感。
    
        Returns:
            List[str]: 符合条件的文件绝对路径列表，按文件名排序（忽略大小写）。
    
        Raises:
            FileNotFoundError: 输入路径不存在。
            PermissionError: 无权限访问输入路径。
            ValueError: 输入路径不是目录。
        """
        # 校验输入路径合法性
        file_path = FileUtil.validate_file_path(file_path)
        
        # 标准化后缀（统一转为小写，支持.pdf/.PDF 等形式）
        normalized_suffix = f".{file_suffix.lower().strip('.')}"
        
        file_list = []
        try:
            for root, _, files in os.walk(file_path):
                # 过滤文件：匹配后缀+按文件名排序
                matched_files = sorted(
                    [f for f in files if f.lower().endswith(normalized_suffix)],
                    key=lambda x: x.lower()  # 忽略大小写排序
                )
                # 拼接绝对路径并添加到结果列表
                file_list.extend([
                    str(Path(root) / file)  # 使用Path确保路径格式统一
                    for file in matched_files
                ])
        except PermissionError as e:
            print(f"无权限访问目录: {file_path}", exc_info=True)
            raise
        except Exception as e:
            print(f"遍历目录时发生未知错误: {file_path}")
            raise
        return file_list

    @staticmethod
    def validate_file_path(file_path: str) -> Path:
        """
        校验输入路径的合法性（存在性、权限、类型）

        Args:
            path (str): 待校验的路径字符串

        Returns:
            Path: 标准化后的绝对路径（Path对象）

        Raises:
            FileNotFoundError: 路径不存在
            PermissionError: 无权限访问路径
            ValueError: 路径不是目录
        """
        path_obj = Path(file_path).absolute()  # 转为绝对路径
        
        if not path_obj.exists():
            print(f"路径不存在: {file_path}")
            raise FileNotFoundError(f"路径不存在: {file_path}")
        if not os.access(path_obj, os.R_OK):
            print(f"无权限访问路径: {file_path}")
            raise PermissionError(f"无权限访问路径: {file_path}")
        if not path_obj.is_dir():
            print(f"路径不是目录: {file_path}")
            raise ValueError(f"路径不是目录: {file_path}")
        
        return path_obj


    @staticmethod
    def check_pdf_integrity_enhanced(pdf_path: str) -> dict:
        """
        增强版PDF完整性检测函数，通过多维度验证确保PDF文件的完整性。

        参数:
            pdf_path (str): 待检测的PDF文件路径。

        返回:
            dict: 包含以下键的字典:
                - is_corrupted (bool): 文件是否损坏。
                - page_count (int): 文件中的页数。
                - error_type (str): 错误类型描述（如果文件损坏）。
                - validation_details (dict): 详细验证结果，包含以下子键:
                    - header_valid (bool): 文件头是否有效。
                    - footer_valid (bool): 文件尾是否有效。
                    - page_content_valid (bool): 页面内容是否有效。
                    - metadata_consistent (bool): 元数据是否一致。
                    - structure_intact (bool): 文件结构是否完整。
                - file_size_bytes (int): 文件大小（字节）。

        功能说明:
            1. 读取文件内容并验证文件头（%PDF-标记）。
            2. 验证文件尾（%%EOF标记）。
            3. 使用PyPDF2解析文件结构，确保页面数量和结构完整性。
            4. 验证页面内容（资源字典和文本提取）。
            5. 检查元数据的基本可读性。
            6. 返回包含所有验证结果的字典。

        异常处理:
            捕获文件读取、解析和内容验证中的异常，并返回相应的错误信息。
        """
        
        result = {
            "is_corrupted": False,
            "page_count": 0,
            "error_type": "",
            "validation_details": {
                "header_valid": False,
                "footer_valid": False,
                "page_content_valid": False,
                "metadata_consistent": False,
                "structure_intact": False
            }
        }

        # 1. 读取文件内容（字节流）
        try:
            with open(pdf_path, 'rb') as f:
                content = f.read()
        except (IOError, OSError) as e:
            result.update({
                "is_corrupted": True,
                "error_type": f"文件无法读取: {str(e)}",
                "validation_details": {"header_valid": False, "footer_valid": False}
            })
            return result

        # 2. 文件头校验
        if len(content) < 5 or not content.startswith(b'%PDF-'):
            result.update({
                "is_corrupted": True,
                "error_type": "PDF文件头无效（缺少%PDF-标记）",
                "validation_details": {"header_valid": False}
            })
            return result
        result["validation_details"]["header_valid"] = True

        # 3. 文件尾校验（检查尾部是否包含%%EOF，允许存在额外字节）
        tail = content[-2048:] if len(content) > 2048 else content
        if b'%%EOF' not in tail:
            result.update({
                "is_corrupted": True,
                "error_type": "PDF文件尾无效（缺少%%EOF标记）",
                "validation_details": {"footer_valid": False}
            })
            return result
        result["validation_details"]["footer_valid"] = True

        # 4. 使用PyPDF2解析结构（通过BytesIO避免关闭句柄问题）
        try:
            reader = PdfReader(io.BytesIO(content))
            num_pages = len(reader.pages)
            result["page_count"] = num_pages
            result["validation_details"]["structure_intact"] = True
        except Exception as e:
            result.update({
                "is_corrupted": True,
                "error_type": f"PDF结构解析失败: {str(e)}",
                "validation_details": {"structure_intact": False}
            })
            return result

        # 5. 页面内容基本验证：访问页面对象属性以触发解析
        try:
            has_valid_content = False
            for i in range(num_pages):
                page = reader.pages[i]
                # 访问媒介框触发解析
                _ = page.mediabox
                # 尝试提取文本，但不将文本为空视为破损
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                # 检查资源字典（可能为None），若资源与文本都为空，判定该页无法验证
                resources = page.get('/Resources') if hasattr(page, 'get') else None
                if resources is None and len(text.strip()) == 0:
                    raise ValueError(f"第{i+1}页无法验证内容（缺少资源且无文本）")
                has_valid_content = True
            result["validation_details"]["page_content_valid"] = has_valid_content
        except Exception as e:
            result.update({
                "is_corrupted": True,
                "error_type": f"页面内容验证失败: {str(e)}",
                "validation_details": {"page_content_valid": False}
            })
            return result

        # 6. 元数据基本可读性（存在即认为基本一致）
        try:
            metadata = reader.metadata
            result["validation_details"]["metadata_consistent"] = bool(metadata)
        except Exception:
            result["validation_details"]["metadata_consistent"] = False

        result["file_size_bytes"] = os.path.getsize(pdf_path)

        return result

if __name__ == '__main__':
    # # 示例用法
    # file_path = "/Volumes/james1t/_AllDocMap/02_Project/mineru_proj/dt=2025-08-06/output_path"

    # file_list = FileUtil.query_file_names_from_folder(file_path, file_suffix='pdf')
    # for pdf_file in file_list:
    #     ret = FileUtil.check_pdf_integrity_enhanced(pdf_file)
        
    #     if ret['is_corrupted'] == True:
    #         print(f"corrupted: {pdf_file}")
    #     else:
    #         print(f"page_count = {ret['page_count']}, file_size_bytes = {ret['file_size_bytes']}: {pdf_file}")

    # print(len(file_list))

    # pdf_file = "/Volumes/james1t/_AllDocMap/04_eBook/书籍--父与子的编程之旅_与小卡特一起学Python.pdf"
    # pdf_file = file_list[0]
    # print(pdf_file)
    # ret = FileUtil.check_pdf_integrity_enhanced(pdf_file)
    # print(ret['is_corrupted'])


    # pdf_file = '/Volumes/james1t/_AllDocMap/02_Project/mineru_proj/dt=2025-08-01/input_path/LGTM_数据标准_CMMI--Neoway-DMM-Case-Study-20-Nov-2015.pdf'
    # df = FileUtil.extract_pdf_content_with_mineru(pdf_file, "/Users/Shared/_AllDocMap/02_Project/gitee/james-python/_data/mineru/")
    # print(df)

    pdf_file = '/home/jiangqian/Documents/_AllDocMap/04_eBook/_LGTM_神策/神策埋点资产管理 -简洁版.pdf'
    ret = FileUtil.get_file_hash(pdf_file)
    print("-" * 128)
    print(ret)