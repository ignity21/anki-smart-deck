from typing import List, Dict, Optional
from anki_smart_deck.config import get_config

from googleapiclient.discovery import build
from rich import print as rprint


class GoogleImageSearchService:
    def __init__(self):
        app_config = get_config()
        self._api_key = app_config.google_search_key
        self._cse_id = app_config.google_cse_id
        self._service = build("customsearch", "v1", developerKey=self._api_key)

    def search_images(
        self,
        query: str,
        num_results: int = 5,
        img_size: str = "MEDIUM",
        img_type: Optional[str] = None,
        safe: str = "active",
    ) -> List[Dict]:
        """
        搜索图片

        Args:
            query: 搜索关键词
            num_results: 返回结果数量 (1-10)
            img_size: 图片大小 (ICON, SMALL, MEDIUM, LARGE, XLARGE, XXLARGE, HUGE)
            img_type: 图片类型 (clipart, face, lineart, stock, photo, animated)
            safe: 安全搜索级别 (active, off)

        Returns:
            图片信息列表，每个元素包含 url, title, width, height 等信息
        """
        # 确保 img_size 是大写
        img_size = img_size.upper()

        rprint(f"🔍 [bold cyan]搜索图片:[/bold cyan] [yellow]{query}[/yellow]")

        try:
            # 构建搜索请求
            search_params = {
                "q": query,
                "cx": self._cse_id,
                "searchType": "image",
                "num": min(num_results, 10),  # API 最多返回 10 个结果
                "imgSize": img_size,
                "safe": safe,
            }

            # 添加可选参数
            if img_type:
                search_params["imgType"] = img_type

            # 执行搜索
            result = self._service.cse().list(**search_params).execute()

            # 解析结果
            images = []
            if "items" in result:
                for item in result["items"]:
                    image_info = {
                        "url": item["link"],
                        "title": item.get("title", ""),
                        "thumbnail": item.get("image", {}).get("thumbnailLink", ""),
                        "width": item.get("image", {}).get("width", 0),
                        "height": item.get("image", {}).get("height", 0),
                        "context_link": item.get("image", {}).get("contextLink", ""),
                        "mime_type": item.get("mime", ""),
                    }
                    images.append(image_info)

                rprint(
                    f"✅ [green]找到 {len(images)} 张图片[/green] [dim](大小: {img_size})[/dim]"
                )

                # 显示前3个结果的预览
                for i, img in enumerate(images[:3], 1):
                    rprint(
                        f"  [cyan]{i}.[/cyan] [dim]{img['title'][:50]}... ({img['width']}x{img['height']})[/dim]"
                    )
            else:
                rprint("[yellow]⚠️  没有找到相关图片[/yellow]")

            return images

        except Exception as e:
            rprint(f"[red]❌ 搜索失败: {str(e)}[/red]")
            return []

    def search_word_image(
        self,
        word: str,
        num_results: int = 3,
        img_size: str = "SMALL",
        prefer_simple: bool = True,
    ) -> List[Dict]:
        """
        专门用于搜索单词相关的图片（适合 Anki 卡片）

        Args:
            word: 单词
            num_results: 返回结果数量
            img_size: 图片大小 (建议 ICON, SMALL, MEDIUM)
            prefer_simple: 是否优先搜索简单图片（clipart/lineart）

        Returns:
            图片信息列表
        """
        # 优化搜索词，增加 "definition" 或 "illustration" 提高相关性
        search_query = f"{word} definition illustration"

        # 如果优先简单图片，先尝试搜索 clipart
        if prefer_simple:
            rprint(
                f"🎨 [bold cyan]搜索简单图示:[/bold cyan] [yellow]{word}[/yellow]"
            )
            images = self.search_images(
                query=search_query,
                num_results=num_results,
                img_size=img_size,
                img_type="clipart",
            )

            # 如果 clipart 结果不够，再搜索普通图片
            if len(images) < num_results:
                rprint("[dim]📸 补充搜索普通图片...[/dim]")
                additional_images = self.search_images(
                    query=search_query,
                    num_results=num_results - len(images),
                    img_size=img_size,
                )
                images.extend(additional_images)
        else:
            images = self.search_images(
                query=search_query, num_results=num_results, img_size=img_size
            )

        return images

    def download_image(self, image_url: str) -> Optional[bytes]:
        """
        下载图片

        Args:
            image_url: 图片 URL

        Returns:
            图片二进制数据，失败返回 None
        """
        import urllib.request

        try:
            rprint(f"⬇️  [cyan]下载图片:[/cyan] [dim]{image_url[:60]}...[/dim]")

            # 添加 User-Agent 避免被某些网站拒绝
            req = urllib.request.Request(
                image_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                image_data = response.read()

            image_size_kb = len(image_data) / 1024
            rprint(f"✅ [green]下载成功[/green] [dim]({image_size_kb:.1f} KB)[/dim]")

            return image_data

        except Exception as e:
            rprint(f"[red]❌ 下载失败: {str(e)}[/red]")
            return None
