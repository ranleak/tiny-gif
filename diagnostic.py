import psutil
import matplotlib.pyplot as plt
import threading
import time
import os

class SystemMonitor:
    """
    A submodule to monitor system resources (CPU and RAM) in the background
    and generate a graphical report using matplotlib.
    """
    def __init__(self, interval=0.5):
        """
        :param interval: How often (in seconds) to record the system stats.
        """
        self.interval = interval
        self.is_recording = False
        self.thread = None
        self.times = []
        self.cpu_usage = []
        self.ram_usage = []
        self.start_time = 0

    def start(self):
        """Starts the background recording thread."""
        self.is_recording = True
        self.times.clear()
        self.cpu_usage.clear()
        self.ram_usage.clear()
        self.start_time = time.time()
        
        # Initial call to cpu_percent to calibrate it
        psutil.cpu_percent(interval=None) 
        
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True  # Ensure thread dies if the main program crashes
        self.thread.start()

    def _monitor_loop(self):
        """The core loop that runs in the background collecting data."""
        while self.is_recording:
            current_time = time.time() - self.start_time
            self.times.append(current_time)
            
            # Record CPU and RAM percentages
            self.cpu_usage.append(psutil.cpu_percent(interval=None))
            self.ram_usage.append(psutil.virtual_memory().percent)
            
            time.sleep(self.interval)

    def stop(self, output_filename="diagnostics_plot.png"):
        """
        Stops the recording thread and generates the graph.
        :param output_filename: The name of the PNG file to save the graph as.
        """
        self.is_recording = False
        if self.thread:
            self.thread.join() # Wait for the background thread to finish cleanly
        
        self._plot_data(output_filename)

    def _plot_data(self, output_filename):
        """Generates a PNG line graph of the recorded data."""
        if not self.times:
            print("No diagnostic data was recorded.")
            return

        # Setup the plot style
        plt.figure(figsize=(10, 6))
        
        # Plot CPU and RAM lines
        plt.plot(self.times, self.cpu_usage, label='CPU Usage (%)', color='#00a8ff', linewidth=2.5)
        plt.plot(self.times, self.ram_usage, label='RAM Usage (%)', color='#e84118', linewidth=2.5)
        
        # Add titles and labels
        plt.title('System Resource Usage During Processing', fontsize=14, fontweight='bold', pad=15)
        plt.xlabel('Time (Seconds)', fontsize=12)
        plt.ylabel('Resource Usage (%)', fontsize=12)
        
        # Lock Y-axis between 0 and 100%
        plt.ylim(0, 105) 
        
        # Add legend and grid
        plt.legend(loc='upper right', fontsize=10)
        plt.grid(True, linestyle='--', alpha=0.6)
        
        # Adjust layout and save
        plt.tight_layout()
        try:
            plt.savefig(output_filename, dpi=300, bbox_inches='tight')
            print(f"Diagnostics graph successfully saved to: {output_filename}")
        except Exception as e:
            print(f"Failed to save diagnostics graph: {e}")
        finally:
            plt.close()

# Example usage if you run this script directly to test it
if __name__ == "__main__":
    print("Testing SystemMonitor for 5 seconds...")
    monitor = SystemMonitor(interval=0.2)
    monitor.start()
    
    # Simulate some workload
    for i in range(5):
        time.sleep(1)
        print(f"Working... {i+1}s")
        
    monitor.stop("test_diagnostics.png")