// udp_server.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>
#include <signal.h>
#include <errno.h>

#define PORT 5005
#define BUFFER_SIZE 4096
#define MAX_CLIENTS 10
#define BROADCAST_INTERVAL 1 // seconds

typedef struct {
    struct sockaddr_in address;
    int active;
} client_info;

client_info clients[MAX_CLIENTS];
int server_socket;
int running = 1;

// Signal handler for graceful shutdown
void handle_signal(int sig) {
    printf("\nShutting down server...\n");
    running = 0;
}

// Load JSON data from file
char* load_json_data(const char* filename) {
    FILE* file = fopen(filename, "r");
    if (!file) {
        perror("Error opening file");
        return NULL;
    }

    fseek(file, 0, SEEK_END);
    long length = ftell(file);
    fseek(file, 0, SEEK_SET);

    char* buffer = (char*)malloc(length + 1);
    if (!buffer) {
        fclose(file);
        return NULL;
    }

    fread(buffer, 1, length, file);
    buffer[length] = '\0';
    fclose(file);
    return buffer;
}

// Update timestamp in JSON
void update_timestamp(char* json_data, size_t size) {
    time_t now;
    struct tm* timeinfo;
    char time_str[30];
    
    time(&now);
    timeinfo = gmtime(&now);
    strftime(time_str, sizeof(time_str), "\"%Y-%m-%dT%H:%M:%SZ\"", timeinfo);
    
    // Find and replace the timestamp
    char* timestamp_ptr = strstr(json_data, "\"timestamp\"");
    if (timestamp_ptr) {
        timestamp_ptr = strchr(timestamp_ptr, ':') + 1;
        while (*timestamp_ptr == ' ' || *timestamp_ptr == '\t') timestamp_ptr++;
        if (*timestamp_ptr == '"') {
            char* end_quote = strchr(timestamp_ptr + 1, '"');
            if (end_quote) {
                memmove(timestamp_ptr + 1, time_str, strlen(time_str));
                timestamp_ptr[strlen(time_str) + 1] = '"';
            }
        }
    }
}

int main(int argc, char *argv[]) {
    struct sockaddr_in server_addr, client_addr;
    socklen_t client_len = sizeof(client_addr);
    char buffer[BUFFER_SIZE];
    int opt = 1;
    const char* json_filename;
    
    // Parse command-line arguments
    if (argc > 1) {
        json_filename = argv[1];
    } else {
        json_filename = "live-data.json";  // Default filename
    }
    
    printf("Using JSON file: %s\n", json_filename);
    
    // Initialize clients
    for (int i = 0; i < MAX_CLIENTS; i++) {
        clients[i].active = 0;
    }

    // Create socket
    if ((server_socket = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("Socket creation failed");
        exit(EXIT_FAILURE);
    }

    // Set socket options
    if (setsockopt(server_socket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt))) {
        perror("setsockopt failed");
        close(server_socket);
        exit(EXIT_FAILURE);
    }

    // Configure server address
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(PORT);

    // Bind socket
    if (bind(server_socket, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        perror("Bind failed");
        close(server_socket);
        exit(EXIT_FAILURE);
    }

    printf("UDP Server started on port %d\n", PORT);
    printf("Press Ctrl+C to stop\n");

    // Set up signal handler for graceful shutdown
    signal(SIGINT, handle_signal);

    // Load JSON data
    char* json_data = load_json_data(json_filename);
    if (!json_data) {
        fprintf(stderr, "Failed to load JSON data from %s\n", json_filename);
        close(server_socket);
        return 1;
    }

    // Main server loop
    while (running) {

        json_data = load_json_data(json_filename);
        if (!json_data) {
            fprintf(stderr, "Failed to load JSON data from %s\n", json_filename);
            close(server_socket);
            return 1;
        }

        // Check for new clients (non-blocking)
        fd_set readfds;
        struct timeval tv;
        FD_ZERO(&readfds);
        FD_SET(server_socket, &readfds);
        tv.tv_sec = 0;
        tv.tv_usec = 100000; // 100ms timeout

        int activity = select(server_socket + 1, &readfds, NULL, NULL, &tv);
        
        if (activity > 0 && FD_ISSET(server_socket, &readfds)) {
            // Receive data (this will be the client's "hello" message)
            int bytes_received = recvfrom(server_socket, buffer, BUFFER_SIZE - 1, 0,
                                        (struct sockaddr*)&client_addr, &client_len);
            
            if (bytes_received > 0) {
                buffer[bytes_received] = '\0';
                printf("New client connected: %s:%d\n", 
                      inet_ntoa(client_addr.sin_addr), 
                      ntohs(client_addr.sin_port));
                
                // Add client to list if not already present
                int client_found = 0;
                for (int i = 0; i < MAX_CLIENTS; i++) {
                    if (clients[i].active && 
                        clients[i].address.sin_addr.s_addr == client_addr.sin_addr.s_addr &&
                        clients[i].address.sin_port == client_addr.sin_port) {
                        client_found = 1;
                        break;
                    }
                }
                
                if (!client_found) {
                    for (int i = 0; i < MAX_CLIENTS; i++) {
                        if (!clients[i].active) {
                            clients[i].address = client_addr;
                            clients[i].active = 1;
                            printf("Added client %s:%d to client list\n", 
                                  inet_ntoa(client_addr.sin_addr), 
                                  ntohs(client_addr.sin_port));
                            break;
                        }
                    }
                }
            }
        }

        // Update and broadcast JSON data
        update_timestamp(json_data, strlen(json_data));
        
        // Send to all active clients
        for (int i = 0; i < MAX_CLIENTS; i++) {
            if (clients[i].active) {
                if (sendto(server_socket, json_data, strlen(json_data), 0,
                          (struct sockaddr*)&clients[i].address, 
                          sizeof(clients[i].address)) < 0) {
                    perror("Error sending data");
                    clients[i].active = 0; // Mark as inactive on error
                }
            }
        }

        // Sleep for the broadcast interval
        sleep(BROADCAST_INTERVAL);
    }

    // Cleanup
    free(json_data);
    close(server_socket);
    printf("Server stopped\n");
    return 0;
}