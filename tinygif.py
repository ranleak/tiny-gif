import os
import sys
from PIL import Image, ImageSequence
from rich.console import Console
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

console = Console()

def format_size(size_in_bytes):
    """Format bytes into a human-readable string."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.2f} KB"
    else:
        return f"{size_in_bytes / (1024 * 1024):.2f} MB"

def main():
    console.print(
        Panel.fit(
            "[bold green]🚀 Interactive GIF Optimizer[/bold green]\n"
            "Compress and resize your GIFs with rich terminal controls.",
            border_style="green"
        )
    )

    # --- 1. File Input ---
    while True:
        in_path = Prompt.ask("[cyan]Enter the path to the input GIF[/cyan]")
        in_path = in_path.strip("\"'") # Remove quotes if dragged/dropped into terminal
        
        if not os.path.exists(in_path):
            console.print("[bold red]❌ File not found. Please try again.[/bold red]")
            continue
        if not in_path.lower().endswith('.gif'):
            console.print("[bold yellow]⚠️ Warning: File doesn't have a .gif extension, but we'll try anyway.[/bold yellow]")
        break

    # --- 2. Gather Original Stats ---
    try:
        img = Image.open(in_path)
        original_frames = img.n_frames
        width, height = img.size
        # Get duration of the first frame (in milliseconds)
        orig_duration_ms = img.info.get('duration', 100) 
        if orig_duration_ms == 0:
            orig_duration_ms = 100 # Fallback to prevent division by zero
            
        orig_fps = round(1000 / orig_duration_ms, 2)
        orig_size_bytes = os.path.getsize(in_path)

        table = Table(title="[bold]Original GIF Info[/bold]", show_header=False, box=None)
        table.add_row("📁 [bold]File Size:[/bold]", format_size(orig_size_bytes))
        table.add_row("📐 [bold]Dimensions:[/bold]", f"{width} x {height}")
        table.add_row("🎞️  [bold]Frames:[/bold]", str(original_frames))
        table.add_row("⏱️  [bold]Estimated FPS:[/bold]", str(orig_fps))
        console.print(Panel(table, border_style="blue"))

    except Exception as e:
        console.print(f"[bold red]❌ Failed to load image: {e}[/bold red]")
        sys.exit(1)

    # --- 3. Interactive Prompts ---
    console.print("\n[bold]⚙️  Optimization Settings[/bold]")
    
    colors = IntPrompt.ask("🎨 [cyan]Max Colors (1-256)[/cyan] Lower means smaller file", default=128)
    colors = max(1, min(256, colors))

    fps = IntPrompt.ask("🎞️  [cyan]Target Frame Rate (FPS)[/cyan]", default=15)
    fps = max(1, fps)
    new_duration_ms = int(1000 / fps)

    console.print("\n[bold]🛠️  Advanced Options[/bold]")
    scale_percent = IntPrompt.ask("🔍 [cyan]Resize scale % (1-100)[/cyan] 100 keeps original size", default=100)
    scale_percent = max(1, min(100, scale_percent))

    drop_frames = IntPrompt.ask("✂️  [cyan]Keep every Nth frame[/cyan] (1 = keep all, 2 = keep half, etc.)", default=1)
    drop_frames = max(1, drop_frames)

    # Determine Output Path
    dir_name = os.path.dirname(in_path)
    base_name = os.path.basename(in_path)
    name, ext = os.path.splitext(base_name)
    default_out = os.path.join(dir_name, f"{name}_optimized.gif")
    
    out_path = Prompt.ask("\n💾 [cyan]Output file path[/cyan]", default=default_out)

    # --- 4. Processing ---
    processed_frames = []
    
    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task_id = progress.add_task("[cyan]Processing Frames...", total=original_frames)
        
        try:
            # Iterate through frames
            for i, frame in enumerate(ImageSequence.Iterator(img)):
                progress.update(task_id, advance=1)
                
                # Apply Frame Dropping
                if i % drop_frames != 0:
                    continue

                # Ensure image is in RGBA mode for proper resizing/processing
                f = frame.copy().convert("RGBA")
                
                # Apply Resizing
                if scale_percent < 100:
                    new_w = int(width * (scale_percent / 100))
                    new_h = int(height * (scale_percent / 100))
                    f = f.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                # Apply Color Quantization
                # Convert back to P (Palette) mode to enforce color limits
                f_p = f.quantize(colors=colors, method=Image.Quantize.FASTOCTREE)
                
                processed_frames.append(f_p)
                
        except Exception as e:
            console.print(f"[bold red]❌ Error during processing: {e}[/bold red]")
            sys.exit(1)

    if not processed_frames:
        console.print("[bold red]❌ Error: No frames left after processing![/bold red]")
        sys.exit(1)

    # --- 5. Saving ---
    with console.status("[bold green]Saving optimized GIF to disk...[/bold green]", spinner="dots"):
        try:
            processed_frames[0].save(
                out_path,
                save_all=True,
                append_images=processed_frames[1:],
                optimize=True,
                duration=new_duration_ms,
                loop=img.info.get('loop', 0)
            )
        except Exception as e:
            console.print(f"[bold red]❌ Failed to save GIF: {e}[/bold red]")
            sys.exit(1)

    # --- 6. Results ---
    new_size_bytes = os.path.getsize(out_path)
    reduction = 100 - ((new_size_bytes / orig_size_bytes) * 100)
    
    # Check if it actually saved space
    if reduction > 0:
        color = "green"
        trend = "📉"
    else:
        color = "red"
        trend = "📈"

    res_table = Table(title="\n[bold]Optimization Results[/bold]", box=None)
    res_table.add_column("Metric", style="cyan")
    res_table.add_column("Original")
    res_table.add_column("Optimized")
    
    res_table.add_row("File Size", format_size(orig_size_bytes), f"[{color}]{format_size(new_size_bytes)}[/{color}]")
    res_table.add_row("Frames", str(original_frames), str(len(processed_frames)))
    res_table.add_row("Resolution", f"{width}x{height}", f"{processed_frames[0].width}x{processed_frames[0].height}")
    
    console.print(res_table)
    console.print(f"\n{trend} [bold]Space Saved: [{color}]{reduction:.2f}%[/{color}][/bold]")
    console.print(f"✨ [bold green]Done! Saved to {out_path}[/bold green]\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]Operation cancelled by user.[/bold red]")
        sys.exit(0)