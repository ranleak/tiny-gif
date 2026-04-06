import os
import sys
import numpy as np
from PIL import Image, ImageSequence
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.text import Text

# Initialize rich console
console = Console()

def format_size(size_in_bytes):
    """Format bytes into a human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} TB"

def process_gif(input_path, output_path, tolerance=15, big_brain_mode=False):
    """
    Core smart compression logic.
    Analyzes frame-by-frame deltas and masks out minor visual changes (noise/small details)
    to dramatically improve LZW compression efficiency when saving.
    """
    try:
        img = Image.open(input_path)
    except Exception as e:
        console.print(f"[bold red]Error opening image:[/bold red] {e}")
        return {"success": False}

    # Get total frames if possible for progress bar
    try:
        total_frames = img.n_frames
    except AttributeError:
        total_frames = 100 # Fallback estimate

    frames = []
    durations = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=True
    ) as progress:
        
        # Step 1: Extraction
        extract_task = progress.add_task("[cyan]Extracting frames...", total=total_frames)
        
        for frame in ImageSequence.Iterator(img):
            # Convert to RGBA to standardise channels and handle existing transparency
            frames.append(frame.convert("RGBA"))
            durations.append(frame.info.get('duration', 100))
            progress.update(extract_task, advance=1)
            
        total_frames = len(frames) # Update with exact count
        progress.update(extract_task, completed=total_frames)

        # Step 2: Smart Delta Optimization
        optimize_task = progress.add_task("[magenta]Applying smart inter-frame optimization...", total=total_frames)
        
        np_frames = [np.array(f) for f in frames]
        optimized_frames = [np_frames[0]]
        new_durations = [durations[0]]
        progress.update(optimize_task, advance=1)

        for i in range(1, total_frames):
            prev = optimized_frames[-1]
            curr = np_frames[i]

            # Calculate absolute difference between the current frame and the previous frame
            # Cast to int16 to prevent overflow when subtracting uint8 values
            diff = np.abs(curr.astype(np.int16) - prev.astype(np.int16))
            
            # Sum the differences across the R, G, and B channels (ignoring Alpha for distance)
            color_distance = np.sum(diff[:, :, :3], axis=2)

            # AI/Smart Logic: Create a mask where the visual difference is less than the user tolerance.
            # These are "unneeded details" or noise. We replace them with the previous frame's pixels.
            mask = color_distance < tolerance

            if big_brain_mode:
                changed_pixels = np.count_nonzero(~mask)
                total_pixels = curr.shape[0] * curr.shape[1]
                # If less than 2% of pixels changed significantly, drop the frame
                if (changed_pixels / total_pixels) < 0.02:
                    # Add its duration to the previous frame to keep the animation speed identical
                    new_durations[-1] += durations[i]
                    progress.update(optimize_task, advance=1)
                    continue

            new_curr = curr.copy()
            new_curr[mask] = prev[mask] # Copy unchanged/minor changed pixels from the previous frame

            optimized_frames.append(new_curr)
            new_durations.append(durations[i])
            progress.update(optimize_task, advance=1)

        # Step 3: Encoding and Saving
        save_task = progress.add_task("[green]Encoding and saving optimized GIF...", total=len(optimized_frames))
        
        # Convert back to PIL Image objects
        final_pil_frames = []
        for f in optimized_frames:
            final_pil_frames.append(Image.fromarray(f))
            progress.update(save_task, advance=1)

        # Save using PIL's built-in bounding box optimizer which works perfectly with our modified frames
        final_pil_frames[0].save(
            output_path,
            save_all=True,
            append_images=final_pil_frames[1:],
            duration=new_durations,
            loop=img.info.get('loop', 0),
            optimize=True # Enables bounding box / transparency optimization
        )

    return {
        "success": True,
        "frames_dropped": total_frames - len(optimized_frames),
        "original_frames": total_frames
    }

def main():
    console.clear()
    title = Text("🪄 Smart GIF Compressor", style="bold cyan on dark_blue", justify="center")
    subtitle = Text("Omits tiny unneeded frame changes to dramatically shrink file size.", style="italic white")
    
    panel = Panel(
        title + "\n\n" + subtitle,
        border_style="cyan",
        expand=False
    )
    console.print(panel, justify="center")
    console.print()

    while True:
        # Get Input Path
        input_path = Prompt.ask("[bold yellow]Enter the path to your GIF file[/bold yellow]")
        input_path = input_path.strip("\"'") # Remove quotes if drag-and-dropped
        
        if not os.path.exists(input_path) or not os.path.isfile(input_path):
            console.print("[bold red]❌ File not found. Please try again.[/bold red]\n")
            continue
            
        if not input_path.lower().endswith(".gif"):
            console.print("[bold red]❌ The file does not appear to be a GIF.[/bold red]\n")
            continue
            
        break

    # Generate default output path
    dir_name, file_name = os.path.split(input_path)
    name, ext = os.path.splitext(file_name)
    default_output = os.path.join(dir_name, f"{name}_compressed{ext}")

    output_path = Prompt.ask(
        "[bold yellow]Enter output path[/bold yellow]", 
        default=default_output
    )

    console.print("\n[dim]Tolerance level dictates how aggressively the algorithm removes small frame changes.[/dim]")
    console.print("[dim]• 0-10: Safe, nearly lossless.[/dim]")
    console.print("[dim]• 15-30: Moderate (Recommended), good size reduction.[/dim]")
    console.print("[dim]• 30+: Aggressive, may introduce 'ghosting' artifacts but creates tiny files.[/dim]")
    
    tolerance = IntPrompt.ask("[bold yellow]Enter optimization tolerance (1-100)[/bold yellow]", default=20)
    
    big_brain = Confirm.ask("\n[bold magenta]🧠 Enable 'Big Brain' mode? (Drops nearly identical frames to save more space)[/bold magenta]", default=False)

    console.print("\n[bold cyan]Starting compression...[/bold cyan]")
    
    original_size = os.path.getsize(input_path)
    
    # Process the GIF
    result = process_gif(input_path, output_path, tolerance, big_brain)

    if result.get("success"):
        new_size = os.path.getsize(output_path)
        reduction = 100 - ((new_size / original_size) * 100) if original_size > 0 else 0
        
        # Display Results
        console.print()
        results_text = (
            f"[bold green]✅ Compression Complete![/bold green]\n\n"
            f"[bold]Original Size:[/bold] {format_size(original_size)}\n"
            f"[bold]New Size:[/bold]      {format_size(new_size)}\n"
            f"[bold]Reduction:[/bold]     [bold cyan]{reduction:.1f}%[/bold cyan] smaller\n"
        )
        
        if big_brain:
            results_text += f"[bold magenta]Frames Dropped:[/bold magenta] {result['frames_dropped']} / {result['original_frames']}\n"
            
        if reduction < 0:
            results_text += "\n[bold yellow]Note:[/bold yellow] The file size increased. This can happen on already highly optimized GIFs or very low tolerance settings."
            
        console.print(Panel(results_text, border_style="green", expand=False))
        console.print(f"\n[dim]Saved to: {output_path}[/dim]\n")
    else:
        console.print("\n[bold red]Compression failed.[/bold red]\n")

    if Confirm.ask("Do you want to compress another file?"):
        main()
    else:
        console.print("[bold cyan]Goodbye![/bold cyan]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]Process interrupted by user. Exiting...[/bold red]")
        sys.exit(0)