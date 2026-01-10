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
        # 优化搜索词策略：
        # 1. 优先搜索简单的概念图示
        # 2. 使用 "meaning" 而不是具体词，避免返回社交媒体内容
        # 3. 过滤掉明显不相关的结果
        # 4. 使用 "-word" 排除包含单词文本的图片

        # 如果是多词短语，只取第一个实词
        search_word = word.split()[0] if " " in word else word

        # 构建排除词列表（排除包含单词文本的图片）
        # 不能直接在搜索词中排除，因为我们还是要搜这个词的图
        # 但可以在 title/context 中过滤

        # 过滤不相关结果的辅助函数
        def is_relevant_image(img_info: Dict) -> bool:
            """检查图片是否相关"""
            title = img_info.get("title", "").lower()
            context = img_info.get("context_link", "").lower()

            # 过滤掉包含单词文本的图片（可能是定义截图或文字图）
            # 但要注意：对于像 "apple" 这样的词，"apple" 可能出现在正常图片标题中
            # 所以我们主要过滤包含 "definition", "meaning", "word" 等关键词的组合
            word_lower = search_word.lower()
            suspicious_combinations = [
                f"{word_lower} definition",
                f"{word_lower} meaning",
                f"{word_lower} word",
                f"define {word_lower}",
                f"what is {word_lower}",
                "dictionary",
                "vocabulary",
            ]

            for combo in suspicious_combinations:
                if combo in title or combo in context:
                    return False

            # 过滤掉社交媒体和视频网站
            blacklist = [
                "tiktok", "youtube", "instagram", "facebook",
                "twitter", "reddit", "pinterest",
                "video", "deal", "rooftop", "restaurant",
                "journal", "article", "paper", "research",
                "screenshot", "app", "download", "template",
                "poster", "flyer", "card design", "typography",
            ]

            for item in blacklist:
                if item in title or item in context:
                    return False

            return True

        # 如果优先简单图片，先尝试搜索 clipart
        if prefer_simple:
            rprint(f"🎨 [bold cyan]搜索简单图示:[/bold cyan] [yellow]{search_word}[/yellow]")

            # 策略1: 搜索词义相关的 clipart（避免文字图片）
            images = self.search_images(
                query=f"{search_word} icon clipart -text -definition -dictionary",
                num_results=num_results * 3,  # 多搜索一些，然后过滤
                img_size=img_size,
                img_type="clipart",
            )

            # 过滤相关图片
            images = [img for img in images if is_relevant_image(img)][:num_results]

            # 策略2: 如果结果不够，搜索 illustration
            if len(images) < num_results:
                rprint("[dim]🎨 补充搜索插图...[/dim]")
                additional_images = self.search_images(
                    query=f"{search_word} illustration symbol -text -typography",
                    num_results=(num_results - len(images)) * 3,
                    img_size=img_size,
                    img_type="clipart",
                )
                additional_images = [img for img in additional_images if is_relevant_image(img)]
                images.extend(additional_images[:num_results - len(images)])

            # 策略3: 如果还不够，尝试图标搜索
            if len(images) < num_results:
                rprint("[dim]🔍 补充搜索图标...[/dim]")
                additional_images = self.search_images(
                    query=f"{search_word} icon vector -word -dictionary",
                    num_results=(num_results - len(images)) * 3,
                    img_size=img_size,
                )
                additional_images = [img for img in additional_images if is_relevant_image(img)]
                images.extend(additional_images[:num_results - len(images)])
        else:
            images = self.search_images(
                query=f"{search_word} image -text -definition",
                num_results=num_results * 3,
                img_size=img_size,
            )
            images = [img for img in images if is_relevant_image(img)][:num_results]




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
