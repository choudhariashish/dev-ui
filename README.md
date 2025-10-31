# UDP JSON Streaming and Visualization System

A real-time data streaming and visualization system that uses UDP for lightweight communication and provides a web-based dashboard for monitoring sensor data.

![Dashboard Preview](https://via.placeholder.com/800x400?text=Dashboard+Preview)  
*Figure: Web Dashboard with Real-time Sensor Data*

## Features

- **UDP Server (C)**: Lightweight server that broadcasts JSON data to connected clients
- **Web Dashboard**: Real-time visualization of sensor data with a clean, responsive UI
- **Data Format**: Standardized JSON format for easy integration with other systems
- **Cross-Platform**: Works on any system with Python 3.x and a C compiler
- **Real-time Updates**: Data updates every second with timestamps

## Prerequisites

- Python 3.6+
- C Compiler (gcc, clang, or MSVC)
- Web Browser (Chrome, Firefox, Safari, or Edge)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/choudhariashish/dev-ui.git
   cd dev-ui
   ```

2. Compile the UDP server:
   ```bash
   gcc udp_server.c -o udp_server
   ```

## Usage

1. Start the UDP server:
   ```bash
   ./udp_server
   ```

2. In a new terminal, start the web client:
   ```bash
   python3 udp_client.py
   ```

3. Open your web browser and navigate to:
   ```
   http://localhost:8000
   ```

## Project Structure

```
dev-ui/
├── udp_server.c    # C implementation of the UDP server
├── udp_client.py   # Python client with web interface
├── index.html     # Web dashboard
├── live-data.json # Sample JSON data
└── README.md      # This file
```

## Configuration

Edit `live-data.json` to customize the sensor data format. The server will automatically detect changes and broadcast updates.

## License

This project is open source and available under the [MIT License](LICENSE).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Author

[Ashish Choudhari](https://github.com/choudhariashish)

---

*Built with ❤️ for real-time data visualization*