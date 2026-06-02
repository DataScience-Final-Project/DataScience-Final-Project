import { Injectable, UnauthorizedException } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { createHmac, timingSafeEqual } from "node:crypto";
import type { JwtPayload } from "./auth.types";

@Injectable()
export class JwtService {
    constructor(private readonly config: ConfigService) { }

    sign(payload: Omit<JwtPayload, 'iat' | 'exp'>, expiresInSeconds: number): string {
        const issuedAt = Math.floor(Date.now() / 1000);
        const fullPayload: JwtPayload = {
            ...payload,
            iat: issuedAt,
            exp: issuedAt + expiresInSeconds,
        };

        const encodedHeader = this.encodeJson({ alg: 'HS256', typ: 'JWT' });
        const encodedPayload = this.encodeJson(fullPayload);
        const signature = this.signSegments(encodedHeader, encodedPayload);

        return `${encodedHeader}.${encodedPayload}.${signature}`;
    }

    verify(token: string): JwtPayload {
        const parts = token.split('.');
        if (parts.length !== 3) {
            throw new UnauthorizedException('Invalid authentication token');
        }

        const [encodedHeader, encodedPayload, signature] = parts;
        const header = this.decodeJson<{ alg?: string; typ?: string }>(encodedHeader);
        if (header.alg !== 'HS256' || header.typ !== 'JWT') {
            throw new UnauthorizedException('Invalid authentication token');
        }

        const expectedSignature = this.signSegments(encodedHeader, encodedPayload);

        if (!this.safeCompare(signature, expectedSignature)) {
            throw new UnauthorizedException('Invalid authentication token');
        }

        const payload = this.decodeJson<JwtPayload>(encodedPayload);

        if (!this.isValidPayload(payload) || payload.exp <= Math.floor(Date.now() / 1000)) {
            throw new UnauthorizedException('Expired authentication token');
        }

        return payload;
    }

    private encodeJson(value: unknown): string {
        return Buffer.from(JSON.stringify(value)).toString('base64url');
    }

    private decodeJson<T>(value: string): T {
        try {
            return JSON.parse(Buffer.from(value, 'base64url').toString('utf8')) as T;
        } catch {
            throw new UnauthorizedException('Invalid authentication token');
        }
    }

    private signSegments(encodedHeader: string, encodedPayload: string): string {
        return createHmac('sha256', this.getSecret())
            .update(`${encodedHeader}.${encodedPayload}`)
            .digest('base64url');
    }

    private safeCompare(left: string, right: string): boolean {
        const leftBuffer = Buffer.from(left, 'base64url');
        const rightBuffer = Buffer.from(right, 'base64url');

        return leftBuffer.length === rightBuffer.length && timingSafeEqual(leftBuffer, rightBuffer);
    }

    private isValidPayload(payload: JwtPayload): boolean {
        return Number.isInteger(payload.sub)
            && typeof payload.email === 'string'
            && typeof payload.username === 'string'
            && Number.isInteger(payload.iat)
            && Number.isInteger(payload.exp);
    }

    private getSecret(): string {
        const secret = this.config.get<string>('JWT_SECRET');
        if (!secret || secret.length < 32) {
            throw new Error('JWT_SECRET must be set to at least 32 characters.');
        }

        return secret;
    }
}
