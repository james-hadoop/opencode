import os
import subprocess

class PdfUtil:
    SOFFICE_PATH = '/Applications/LibreOffice.app/Contents/MacOS/soffice'

    @staticmethod
    def word_to_pdf(input_path: str, output_path: str = None):
        """
        将Word文档转换为PDF（支持单个文件或目录批量转换）
        :param input_path: Word文档路径（.doc或.docx格式）或目录
        :param output_path: 输出PDF路径，若为目录则在指定目录下生成，若为None则与原文件同目录
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"路径不存在：{input_path}")

        if os.path.isdir(input_path):
            return PdfUtil._batch_convert_dir(input_path, output_path)

        if not input_path.lower().endswith(('.doc', '.docx')):
            raise ValueError("仅支持 .doc 或 .docx 格式的Word文档")

        filename = os.path.splitext(os.path.basename(input_path))[0] + '.pdf'
        if output_path is None:
            output_path = os.path.splitext(input_path)[0] + '.pdf'
        elif os.path.isdir(output_path):
            output_path = os.path.join(output_path, filename)

        output_dir = os.path.dirname(os.path.abspath(output_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        try:
            subprocess.run([
                PdfUtil.SOFFICE_PATH,
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', output_dir,
                input_path
            ], check=True, capture_output=True, text=True)

            if os.path.exists(output_path):
                print(f"转换成功！PDF文件已保存至：{output_path}")
                return True
            else:
                print(f"转换成功但文件未找到，请检查：{output_path}")
                return False
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"转换失败：{str(e)}")
            return False

    @staticmethod
    def _batch_convert_dir(input_dir: str, output_dir: str = None) -> int:
        """批量转换目录中的所有Word文档"""
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        success_count = fail_count = 0
        for filename in os.listdir(input_dir):
            if filename.lower().endswith(('.doc', '.docx')):
                print(f"\n正在处理：{filename}")
                if PdfUtil.word_to_pdf(os.path.join(input_dir, filename), output_dir):
                    success_count += 1
                else:
                    fail_count += 1

        print(f"\n批量转换完成！成功：{success_count}，失败：{fail_count}")
        return success_count

# 示例调用
if __name__ == "__main__":
    input_path = "/Volumes/james1t/proj_openclaw/气象数据/6.1 国家站（含雷电）"
    output_path = "/Volumes/james1t/proj_openclaw/气象数据/_6.1 国家站（含雷电）"
    
    PdfUtil.word_to_pdf(input_path, output_path)