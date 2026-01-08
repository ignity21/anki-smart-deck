#!/usr/bin/env python
from rich import print as rprint

from anki_smart_deck.services.image_search import GoogleImageSearchService


def main():
    # 使用示例
    rprint("\n" + "=" * 60)
    rprint("Google Image Search Service - 使用示例")
    rprint("=" * 60 + "\n")

    # 创建服务实例
    service = GoogleImageSearchService()

    # 示例 1: 搜索单词图片
    rprint("\n[bold]--- 示例 1: 搜索单词图片 (适合 Anki) ---[/bold]")
    word = "apple"
    images = service.search_word_image(
        word=word, num_results=2, img_size="MEDIUM", prefer_simple=True
    )

    if images:
        rprint(f"\n找到 {len(images)} 张图片:")
        for i, img in enumerate(images, 1):
            rprint(f"[cyan]{i}.[/cyan] {img['title']}")
            rprint(f"   URL: {img['url']}")
            rprint(f"   尺寸: {img['width']}x{img['height']}")
            rprint()

    # 示例 2: 搜索普通图片
    rprint("\n[bold]--- 示例 2: 搜索普通图片 ---[/bold]")
    images = service.search_images(
        query="python programming", num_results=2, img_size="MEDIUM"
    )

    # 示例 3: 下载图片
    rprint("\n[bold]--- 示例 3: 下载图片 ---[/bold]")
    if images and len(images) > 0:
        first_image = images[0]
        image_data = service.download_image(first_image["url"])
        if image_data:
            # 保存到文件
            output_file = "downloaded_image.jpg"
            with open(output_file, "wb") as f:
                f.write(image_data)
            rprint(f"[green]💾 图片已保存到: {output_file}[/green]")

    rprint("\n" + "=" * 60)
    rprint("示例运行完成!")
    rprint("=" * 60 + "\n")


if __name__ == "__main__":
    main()
