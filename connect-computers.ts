/**
 * ZeXis State Share - Computer Connection Module
 * Handles direct peer-to-peer or relay-based state transfer between ZeXis machines
 */

import * as net from 'net';
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

interface ConnectionConfig {
  mode: 'direct' | 'relay';
  targetIP?: string;
  targetPort?: number;
  relayServer?: string;
  encryptionKey?: string;
}

class StateShareConnection {
  private config: ConnectionConfig;
  private socket: net.Socket | null = null;

  constructor(config: ConnectionConfig) {
    this.config = config;
  }

  /**
   * Establish connection to target machine
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.config.mode === 'direct') {
        if (!this.config.targetIP || !this.config.targetPort) {
          reject(new Error('Direct mode requires targetIP and targetPort'));
          return;
        }

        this.socket = net.createConnection(
          {
            host: this.config.targetIP,
            port: this.config.targetPort,
          },
          () => {
            console.log(`Connected to ${this.config.targetIP}:${this.config.targetPort}`);
            resolve();
          }
        );

        this.socket.on('error', (err: Error) => {
          reject(err);
        });
      } else if (this.config.mode === 'relay') {
        // Relay mode implementation would connect to relay server
        reject(new Error('Relay mode not yet implemented'));
      }
    });
  }

  /**
   * Send .xis file to connected machine
   */
  async sendStateFile(xisFilePath: string): Promise<void> {
    if (!this.socket) {
      throw new Error('Not connected');
    }

    const fileData = fs.readFileSync(xisFilePath);
    let dataToSend: Buffer = fileData;

    // Optional encryption
    if (this.config.encryptionKey) {
      dataToSend = this.encrypt(fileData, this.config.encryptionKey);
    }

    // Send file size first
    const sizeBuffer = Buffer.alloc(8);
    sizeBuffer.writeBigUInt64BE(BigInt(dataToSend.length));
    this.socket.write(sizeBuffer);

    // Send file data
    this.socket.write(dataToSend);

    console.log(`Sent ${xisFilePath} (${dataToSend.length} bytes)`);
  }

  /**
   * Receive .xis file from connected machine
   */
  async receiveStateFile(outputPath: string): Promise<void> {
    if (!this.socket) {
      throw new Error('Not connected');
    }

    return new Promise<void>((resolve, reject) => {
      let fileSize: bigint | null = null;
      let receivedData = Buffer.alloc(0);

      const dataHandler = (chunk: Buffer): void => {
        if (fileSize === null) {
          // First 8 bytes are file size
          fileSize = chunk.readBigUInt64BE(0);
          receivedData = chunk.slice(8);
        } else {
          receivedData = Buffer.concat([receivedData, chunk]);
        }

        // Check if we received all data
        if (fileSize !== null && BigInt(receivedData.length) >= fileSize) {
          const finalData: Buffer = receivedData.slice(0, Number(fileSize));

          // Decrypt if needed
          const processedData: Buffer = this.config.encryptionKey
            ? this.decrypt(finalData, this.config.encryptionKey)
            : finalData;

          fs.writeFileSync(outputPath, processedData);
          console.log(`Received state file: ${outputPath}`);
          resolve();
        }
      };

      const errorHandler = (err: Error): void => {
        reject(err);
      };

      this.socket!.on('data', dataHandler);
      this.socket!.on('error', errorHandler);
    });
  }

  /**
   * Close connection
   */
  disconnect(): void {
    if (this.socket) {
      this.socket.end();
      this.socket = null;
    }
  }

  /**
   * Simple AES-256-CBC encryption
   */
  private encrypt(data: Buffer, key: string): Buffer {
    const keyHash = crypto.createHash('sha256').update(key).digest();
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv('aes-256-cbc', keyHash, iv);
    const encrypted = Buffer.concat([cipher.update(data), cipher.final()]);
    return Buffer.concat([iv, encrypted]);
  }

  /**
   * Simple AES-256-CBC decryption
   */
  private decrypt(data: Buffer, key: string): Buffer {
    const keyHash = crypto.createHash('sha256').update(key).digest();
    const iv = data.slice(0, 16);
    const encrypted = data.slice(16);
    const decipher = crypto.createDecipheriv('aes-256-cbc', keyHash, iv);
    return Buffer.concat([decipher.update(encrypted), decipher.final()]);
  }
}

/**
 * Create a listener server for incoming state transfers
 */
export function createStateShareServer(port: number, onReceive: (filePath: string) => void): net.Server {
  const server = net.createServer((socket: net.Socket) => {
    console.log('Client connected');

    let fileSize: bigint | null = null;
    let receivedData = Buffer.alloc(0);

    socket.on('data', (chunk: Buffer) => {
      if (fileSize === null) {
        fileSize = chunk.readBigUInt64BE(0);
        receivedData = chunk.slice(8);
      } else {
        receivedData = Buffer.concat([receivedData, chunk]);
      }

      if (fileSize !== null && BigInt(receivedData.length) >= fileSize) {
        const finalData = receivedData.slice(0, Number(fileSize));
        const outputPath = path.join('/tmp', `received-${Date.now()}.xis`);
        fs.writeFileSync(outputPath, finalData);
        console.log(`Received state file: ${outputPath}`);
        onReceive(outputPath);
      }
    });

    socket.on('end', () => {
      console.log('Client disconnected');
    });
  });

  server.listen(port, () => {
    console.log(`State Share server listening on port ${port}`);
  });

  return server;
}

export { StateShareConnection, ConnectionConfig };