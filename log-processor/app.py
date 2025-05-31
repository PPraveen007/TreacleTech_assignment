#importing dependencies
import re
import ipaddress
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import sys
import os
from typing import Set, Dict, List
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IPProcessor:
    def __init__(self, mongo_uri=os.environ.get('MONGODB_URI', 'mongodb://admin:password123@mongodb:27017/ip_database?authSource=admin')):
        """Initialize the IP processor with MongoDB connection"""
        self.mongo_uri = mongo_uri
        self.client = None
        self.db = None
        
        # IP regex pattern - matches IPv4 addresses
        self.ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
        
        # Private IP ranges (IPv4) as given in the assignment PDF
        self.private_ranges = [
            ipaddress.IPv4Network('10.0.0.0/8'),
            ipaddress.IPv4Network('172.16.0.0/12'),
            ipaddress.IPv4Network('192.168.0.0/16')
        ]
        
        # Statistics to check and validate the results are correct
        self.stats = {
            'total_lines_processed': 0,
            'total_ips_found': 0,
            'unique_public_ips_stored': 0,
            'unique_private_ips_stored': 0,
            'duplicate_ips_skipped': 0,
            'within_file_duplicates': 0
        }
    
    def connect_to_mongodb(self):
        """Establish connection to MongoDB"""
        try:
            logger.info(f"Connecting to MongoDB using URI: {self.mongo_uri}")
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            
            # Test the connection
            self.client.admin.command('ping')
            self.db = self.client.get_database('ip_database')
            
            # Create collections if they don't exist
            self.public_ips_collection = self.db['public_ips']
            self.private_ips_collection = self.db['private_ips']
            
            # Create unique indexes to prevent duplicates on IP addresses
            self.public_ips_collection.create_index("ip", unique=True)
            self.private_ips_collection.create_index("ip", unique=True)
            
            logger.info("Successfully connected to MongoDB")
            return True
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            return False
    
    def is_valid_ip(self, ip_str: str) -> bool:
        """Validate if string is a valid IPv4 address or not"""
        try:
            ipaddress.IPv4Address(ip_str)
            return True
        except ipaddress.AddressValueError:
            return False
    
    def is_private_ip(self, ip_str: str) -> bool:
        """Check if IP address is in private ranges"""
        try:
            ip = ipaddress.IPv4Address(ip_str)
            return any(ip in network for network in self.private_ranges)
        except ipaddress.AddressValueError:
            return False
    
    def extract_ips_from_line(self, line: str) -> List[str]:
        """Extract all valid IP addresses from a log line"""
        # Find all potential IP addresses using regex
        potential_ips = self.ip_pattern.findall(line)
        
        # Filter out invalid IPs and return valid ones
        valid_ips = []
        for ip in potential_ips:
            if self.is_valid_ip(ip):
                valid_ips.append(ip)
        
        return valid_ips
    
    def store_ip_in_mongodb(self, ip: str, is_private: bool) -> bool:
        """Store IP in appropriate MongoDB collection"""
        try:
            collection = self.private_ips_collection if is_private else self.public_ips_collection
            ip_type = "private" if is_private else "public"
            
            document = {
                "ip": ip,
                "type": ip_type,
                "first_seen": None  # You can add timestamp if needed as for now from development perspective I are not storing it
            }
            
            # Use upsert to avoid duplicates
            result = collection.update_one(
                {"ip": ip},
                {"$setOnInsert": document},
                upsert=True
            )
            
            if result.upserted_id:
                logger.debug(f"Inserted new {ip_type} IP: {ip}")
                return True
            else:
                logger.debug(f"Duplicate {ip_type} IP already in database: {ip}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing IP {ip}: {e}")
            return False
    
    def process_log_file(self, log_file_path: str):
        """Process the log file line by line"""
        if not os.path.exists(log_file_path):
            logger.error(f"Log file not found: {log_file_path}")
            return False
        
        logger.info(f"Starting to process log file: {log_file_path}")
        
        # Track unique IPs within this file to avoid processing duplicates
        processed_ips = set()
        
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as file:
                for line_num, line in enumerate(file, 1):
                    self.stats['total_lines_processed'] += 1
                    
                    # Extract IPs from current line
                    ips_in_line = self.extract_ips_from_line(line.strip())
                    
                    for ip in ips_in_line:
                        self.stats['total_ips_found'] += 1
                        
                        # Skip if we've already processed this IP in this file
                        if ip in processed_ips:
                            self.stats['within_file_duplicates'] += 1
                            continue
                        
                        processed_ips.add(ip)
                        
                        # Classify and store IP
                        is_private = self.is_private_ip(ip)
                        success = self.store_ip_in_mongodb(ip, is_private)
                        
                        if success:
                            # IP was successfully inserted (new IP) like public or private
                            # logger.info(f"Stored {ip} as {'private' if is_private else 'public'} IP") short way to write but given some error in the code so I have commented it
                            if is_private:
                                self.stats['unique_private_ips_stored'] += 1
                            else:
                                self.stats['unique_public_ips_stored'] += 1
                        else:
                            # IP already existed in database
                            self.stats['duplicate_ips_skipped'] += 1
                    
                    # Progress logging for large files 
                    if line_num % 1000 == 0:
                        logger.info(f"Processed {line_num} lines...")
            
            logger.info("Log file processing completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error processing log file: {e}")
            return False
    
    def print_statistics(self):
        """Print processing statistics"""
        logger.info("=== PROCESSING STATISTICS ===")
        logger.info(f"Total lines processed: {self.stats['total_lines_processed']}")
        logger.info(f"Total IPs found: {self.stats['total_ips_found']}")
        logger.info(f"Within-file duplicates: {self.stats['within_file_duplicates']}")
        logger.info(f"Unique IPs from file: {len(set()) if not hasattr(self, 'processed_ips') else len(getattr(self, 'processed_ips', set()))}")
        logger.info(f"New public IPs stored: {self.stats['unique_public_ips_stored']}")
        logger.info(f"New private IPs stored: {self.stats['unique_private_ips_stored']}")
        logger.info(f"Database duplicates skipped: {self.stats['duplicate_ips_skipped']}")
        
        # Get collection counts from MongoDB
        try:
            public_count = self.public_ips_collection.count_documents({})
            private_count = self.private_ips_collection.count_documents({})
            logger.info(f"Total public IPs in database: {public_count}")
            logger.info(f"Total private IPs in database: {private_count}")
            
            # Math check
            total_unique_from_file = self.stats['unique_public_ips_stored'] + self.stats['unique_private_ips_stored'] + self.stats['duplicate_ips_skipped']
            logger.info(f"Math check - Unique IPs processed: {total_unique_from_file}")
            logger.info(f"Math check - Should equal: {self.stats['total_ips_found'] - self.stats['within_file_duplicates']}")
            
        except Exception as e:
            logger.error(f"Error getting collection counts: {e}")
    
    def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

def main():
    # Get log file path from environment variable or use default
    log_file_path = os.environ.get('LOG_FILE_PATH', '/app/logs/sample.log')
    
    # Initialize processor
    processor = IPProcessor()
    
    try:
        # Connect to MongoDB
        if not processor.connect_to_mongodb():
            logger.error("Failed to connect to MongoDB. Exiting.")
            sys.exit(1)
        
        # Process the log file
        success = processor.process_log_file(log_file_path)
        
        if success:
            processor.print_statistics()
            logger.info("IP processing completed successfully!")
        else:
            logger.error("IP processing failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        processor.close_connection()

if __name__ == "__main__":
    main()