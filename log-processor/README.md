# Log File IP Extraction and Storage System

## Overview

This project provides a containerized solution for extracting IP addresses from log files and storing them in MongoDB. The system categorizes IPs as public or private, handles duplicates efficiently, and provides comprehensive statistics about the processing.

## Features

- **IP Extraction**: Uses regex patterns to extract IPv4 addresses from log files
- **IP Classification**: Automatically categorizes IPs as public or private based on
### Private IP Ranges (IPv4):
  `10.0.0.0` to `10.255.255.255` (10.0.0.0/8)
  `172.16.0.0` to `172.31.255.255` (172.16.0.0/12)
  `192.168.0.0` to `192.168.255.255` (192.168.0.0/16)
- **Duplicate Handling**: Prevents storage of duplicate IPs both within files and across database
- **MongoDB Storage**: Stores IPs in separate collections for public and private addresses
- **Statistics Reporting**: Provides detailed processing statistics
- **Containerized Solution**: Fully dockerized with Docker Compose orchestration
- **Error Handling**: Robust error handling and logging throughout the process

## Project Structure

```
log-processor/
├── app.py                 # Main Python application
├── Dockerfile            # Docker image configuration
├── docker-compose.yml    # Docker Compose orchestration
├── requirements.txt      # Python dependencies
├── README.md            # This documentation
├── logs/                # Directory for log files
│   ├── test.log         # Sample log file
│   └── sample.log       # Additional sample log
└── approach.md          # Detailed technical approach
```

## Dependencies

### System Requirements
- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 512MB RAM available for containers

### Python Dependencies (handled automatically)
- pymongo==4.6.0
- ipaddress (built-in)
- re (built-in)
- logging (built-in)

## Quick Start

1. **Clone or prepare the project directory**:
   ```bash
   mkdir log-processor && cd log-processor
   # Copy all project files to this directory
   ```

2. **Prepare your log files**:
   ```bash
   mkdir -p logs
   # Copy your log files to the logs/ directory
   # Default: logs/test.log
   `******Remember: I have set the log file check to manual in both docker-compose.yml and the Dockerfile. In both files, you need to specify the name of the .log file (e.g., test.log). You can later change this to other log files as needed for different tests.******`
   ```

3. **Build and run the system**:
   ```bash
   docker-compose up --build
   ```

4. **View results**:
   The application will process the log file and display statistics. MongoDB will continue running for data persistence.

## Configuration

### Environment Variables

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `LOG_FILE_PATH` | `/app/logs/test.log` | Path to the log file inside container |
| `MONGODB_URI` | `mongodb://admin:password123@mongodb:27017/ip_database?authSource=admin` | MongoDB connection string |

### MongoDB Configuration

- **Database**: `ip_database`
- **Collections**: 
  - `public_ips`: Stores public IP addresses
  - `private_ips`: Stores private IP addresses
- **Authentication**: Username: `admin`, Password: `password123`
- **Port**: 27017

## Usage Examples

### Basic Usage
```bash
# Process default log file (logs/test.log)
docker-compose up --build
```

### Custom Log File
```bash
# Process a different log file
LOG_FILE_PATH=/app/logs/custom.log docker-compose up --build
```

### View MongoDB Data
```bash
# Connect to MongoDB container
docker exec -it log_processor_mongodb mongosh -u admin -p password123 --authenticationDatabase admin

# View public IPs
use ip_database
db.public_ips.find().pretty()

# View private IPs
db.private_ips.find().pretty()

# Count records
db.public_ips.countDocuments()
db.private_ips.countDocuments()
```

## Log File Format

The system supports various log formats containing IPv4 addresses. Example formats:

### Apache Access Log
```
192.168.1.100 - - [30/May/2025:10:15:30 +0000] "GET / HTTP/1.1" 200 1234
```

### Nginx Access Log
```
203.0.113.45 - user [30/May/2025:10:15:30 +0000] "POST /api HTTP/1.1" 201 567
```

### Custom Application Log
```
2025-05-30 10:15:30 INFO Connection from 10.0.0.5 established
```

## Output and Statistics for the given log.test

The application provides comprehensive statistics:

```
=== PROCESSING STATISTICS ===
Total lines processed: 742
Total IPs found: 377
Within-file duplicates: 308
Unique IPs from file: 0
New public IPs stored: 0
New private IPs stored: 0
Database duplicates skipped: 69
Total public IPs in database: 68
Total private IPs in database: 1
Math check - Unique IPs processed: 69
Math check - Should equal: 69
```
``` for the sample test file the outputs are 
Total IPs found: 60
Within-file duplicates: 6
Unique IPs from file: 0                  
New public IPs stored: 0                 
New private IPs stored: 0                
Database duplicates skipped: 54
Total public IPs in database: 24         
Total private IPs in database: 30        
Math check - Unique IPs processed: 54    
Math check - Should equal: 54
IP processing completed successfully!    
MongoDB connection closed 
```
## Data Storage Schema

### Public IPs Collection
```json
{
  "_id": ObjectId("..."),
  "ip": "203.0.113.45",
  "type": "public",
  "first_seen": null
}
```

### Private IPs Collection
```json
{
  "_id": ObjectId("..."),
  "ip": "192.168.1.100",
  "type": "private",
  "first_seen": null
}
```

## Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   ```
   Solution: Ensure MongoDB container is healthy before app starts
   Check: docker-compose ps
   ```

2. **Log File Not Found**
   ```
   Solution: Ensure log file exists in logs/ directory
   Check: ls -la logs/
   ```

3. **Permission Denied**
   ```
   Solution: Check file permissions on log files
   Fix: chmod 644 logs/*.log
   ```

### Debugging

1. **View container logs**:
   ```bash
   docker-compose logs log_processor
   docker-compose logs mongodb
   ```

2. **Access container shell**:
   ```bash
   docker exec -it log_processor_app /bin/bash
   ```

3. **Check MongoDB status**:
   ```bash
   docker exec -it log_processor_mongodb mongosh --eval "db.runCommand('ping')"
   ```

## Performance Considerations

- **Large Files**: The system processes files line by line for memory efficiency
- **Progress Logging**: Progress is logged every 1000 lines for large files
- **Duplicate Handling**: In-memory set tracking prevents redundant database operations
- **Connection Pooling**: MongoDB connection is maintained throughout processing

## Security Features

- Non-root user execution in containers
- MongoDB authentication enabled
- Read-only log file mounting
- Network isolation through Docker networks

## Extending the System

### Adding New Log Formats
Modify the `extract_ips_from_line` method in `app.py` to handle different log formats.

### Adding Timestamps
Modify the storage schema to include `first_seen` timestamps.

## Stopping the System

```bash
# Stop all containers
docker-compose down

# Stop and remove volumes (deletes all data)
docker-compose down -v
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the detailed approach documentation
3. Examine container logs for specific error messages

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review Docker and MongoDB logs
3. Verify log file format compatibility
4. Check system resources (memory, disk space)