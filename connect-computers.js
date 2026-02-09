"use strict";
/**
 * ZeXis State Share - Computer Connection Module
 * Handles direct peer-to-peer or relay-based state transfer between ZeXis machines
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.StateShareConnection = void 0;
exports.createStateShareServer = createStateShareServer;
const net = __importStar(require("net"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const crypto = __importStar(require("crypto"));
class StateShareConnection {
    config;
    socket = null;
    constructor(config) {
        this.config = config;
    }
    /**
     * Establish connection to target machine
     */
    async connect() {
        return new Promise((resolve, reject) => {
            if (this.config.mode === 'direct') {
                if (!this.config.targetIP || !this.config.targetPort) {
                    reject(new Error('Direct mode requires targetIP and targetPort'));
                    return;
                }
                this.socket = net.createConnection({
                    host: this.config.targetIP,
                    port: this.config.targetPort,
                }, () => {
                    console.log(`Connected to ${this.config.targetIP}:${this.config.targetPort}`);
                    resolve();
                });
                this.socket.on('error', (err) => {
                    reject(err);
                });
            }
            else if (this.config.mode === 'relay') {
                // Relay mode implementation would connect to relay server
                reject(new Error('Relay mode not yet implemented'));
            }
        });
    }
    /**
     * Send .xis file to connected machine
     */
    async sendStateFile(xisFilePath) {
        if (!this.socket) {
            throw new Error('Not connected');
        }
        const fileData = fs.readFileSync(xisFilePath);
        let dataToSend = fileData;
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
    async receiveStateFile(outputPath) {
        if (!this.socket) {
            throw new Error('Not connected');
        }
        return new Promise((resolve, reject) => {
            let fileSize = null;
            let receivedData = Buffer.alloc(0);
            const dataHandler = (chunk) => {
                if (fileSize === null) {
                    // First 8 bytes are file size
                    fileSize = chunk.readBigUInt64BE(0);
                    receivedData = chunk.slice(8);
                }
                else {
                    receivedData = Buffer.concat([receivedData, chunk]);
                }
                // Check if we received all data
                if (fileSize !== null && BigInt(receivedData.length) >= fileSize) {
                    const finalData = receivedData.slice(0, Number(fileSize));
                    // Decrypt if needed
                    const processedData = this.config.encryptionKey
                        ? this.decrypt(finalData, this.config.encryptionKey)
                        : finalData;
                    fs.writeFileSync(outputPath, processedData);
                    console.log(`Received state file: ${outputPath}`);
                    resolve();
                }
            };
            const errorHandler = (err) => {
                reject(err);
            };
            this.socket.on('data', dataHandler);
            this.socket.on('error', errorHandler);
        });
    }
    /**
     * Close connection
     */
    disconnect() {
        if (this.socket) {
            this.socket.end();
            this.socket = null;
        }
    }
    /**
     * Simple AES-256-CBC encryption
     */
    encrypt(data, key) {
        const keyHash = crypto.createHash('sha256').update(key).digest();
        const iv = crypto.randomBytes(16);
        const cipher = crypto.createCipheriv('aes-256-cbc', keyHash, iv);
        const encrypted = Buffer.concat([cipher.update(data), cipher.final()]);
        return Buffer.concat([iv, encrypted]);
    }
    /**
     * Simple AES-256-CBC decryption
     */
    decrypt(data, key) {
        const keyHash = crypto.createHash('sha256').update(key).digest();
        const iv = data.slice(0, 16);
        const encrypted = data.slice(16);
        const decipher = crypto.createDecipheriv('aes-256-cbc', keyHash, iv);
        return Buffer.concat([decipher.update(encrypted), decipher.final()]);
    }
}
exports.StateShareConnection = StateShareConnection;
/**
 * Create a listener server for incoming state transfers
 */
function createStateShareServer(port, onReceive) {
    const server = net.createServer((socket) => {
        console.log('Client connected');
        let fileSize = null;
        let receivedData = Buffer.alloc(0);
        socket.on('data', (chunk) => {
            if (fileSize === null) {
                fileSize = chunk.readBigUInt64BE(0);
                receivedData = chunk.slice(8);
            }
            else {
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
