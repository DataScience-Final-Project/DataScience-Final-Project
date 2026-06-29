import {
    BadRequestException,
    ConflictException,
    Injectable,
    UnauthorizedException,
} from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { InjectModel } from "@nestjs/sequelize";
import { randomBytes, scrypt, timingSafeEqual } from "node:crypto";
import { promisify } from "node:util";
import { Op } from "sequelize";
import { User } from "../entities/user/user.model";
import type { LoginRequest, SignupRequest } from "./auth.dto";
import type { AuthenticatedRequest, PublicUser } from "./auth.types";
import { JwtService } from "./jwt.service";

const scryptAsync = promisify(scrypt) as (password: string, salt: Buffer, keyLength: number) => Promise<Buffer>;
const PASSWORD_HASH_BYTES = 64;
const PASSWORD_SALT_BYTES = 16;
const PASSWORD_ALGORITHM = 'scrypt';
export const AUTH_COOKIE_NAME = 'auth_token';

type AuthSession = {
    token: string;
    user: PublicUser;
    maxAgeMs: number;
};

type NormalizedSignup = {
    email: string;
    phone: string;
    username: string;
    firstName: string;
    lastName: string;
    password: string;
};

@Injectable()
export class AuthService {
    constructor(
        @InjectModel(User) private readonly userModel: typeof User,
        private readonly config: ConfigService,
        private readonly jwtService: JwtService,
    ) { }

    async signup(dto: SignupRequest): Promise<AuthSession> {
        const normalized = this.normalizeSignup(dto);
        const existingUser = await this.userModel.findOne({
            where: {
                [Op.or]: [
                    { email: normalized.email },
                    { phone: normalized.phone },
                    { username: normalized.username },
                ],
            },
        });

        if (existingUser) {
            throw new ConflictException('Email, phone, or username is already registered');
        }

        const password = await this.hashPassword(normalized.password);
        const user = await this.userModel.create({
            email: normalized.email,
            phone: normalized.phone,
            username: normalized.username,
            firstName: normalized.firstName,
            lastName: normalized.lastName,
            passwordHash: password.hash,
            passwordSalt: password.salt,
            passwordAlgorithm: PASSWORD_ALGORITHM,
        });

        return this.createSession(user);
    }

    async login(dto: LoginRequest): Promise<AuthSession> {
        const identifier = this.normalizeRequired(dto.identifier ?? dto.email ?? dto.username ?? dto.phone, 'identifier');
        const password = this.normalizeRequired(dto.password, 'password');
        const user = await this.userModel.findOne({
            where: {
                [Op.or]: [
                    { email: identifier.toLowerCase() },
                    { phone: identifier },
                    { username: identifier },
                ],
            },
        });

        if (!user || !(await this.verifyPassword(password, user.passwordSalt, user.passwordHash))) {
            throw new UnauthorizedException('Invalid credentials');
        }

        return this.createSession(user);
    }

    async authenticateRequest(request: AuthenticatedRequest): Promise<PublicUser> {
        const token = this.extractAuthCookie(request);
        if (!token) {
            throw new UnauthorizedException('Missing authentication cookie');
        }

        const payload = this.jwtService.verify(token);
        const user = await this.userModel.findByPk(payload.sub);

        if (!user) {
            throw new UnauthorizedException('Invalid authentication token');
        }

        return this.toPublicUser(user);
    }

    getCookieName(): string {
        return this.config.get<string>('JWT_COOKIE_NAME', AUTH_COOKIE_NAME);
    }

    getCookieMaxAgeMs(): number {
        return this.getExpiresInSeconds() * 1000;
    }

    useSecureCookies(): boolean {
        return this.config.get<string>('NODE_ENV') === 'production';
    }

    private createSession(user: User): AuthSession {
        const publicUser = this.toPublicUser(user);
        const expiresInSeconds = this.getExpiresInSeconds();
        const token = this.jwtService.sign({
            sub: publicUser.userId,
            email: publicUser.email,
            username: publicUser.username,
        }, expiresInSeconds);

        return {
            token,
            user: publicUser,
            maxAgeMs: expiresInSeconds * 1000,
        };
    }

    private normalizeSignup(dto: SignupRequest): NormalizedSignup {
        const email = this.normalizeRequired(dto.email, 'email').toLowerCase();
        const phone = this.normalizeRequired(dto.phone, 'phone');
        const username = this.normalizeRequired(dto.username, 'username');
        const firstName = this.normalizeRequired(dto.firstName ?? dto.first_name, 'firstName');
        const lastName = this.normalizeRequired(dto.lastName ?? dto.last_name, 'lastName');
        const password = this.normalizeRequired(dto.password, 'password');

        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            throw new BadRequestException('Invalid email');
        }

        if (phone.length < 6 || phone.length > 30) {
            throw new BadRequestException('Phone must be between 6 and 30 characters');
        }

        if (username.length < 3 || username.length > 50) {
            throw new BadRequestException('Username must be between 3 and 50 characters');
        }

        if (firstName.length > 50) {
            throw new BadRequestException('First name must be 50 characters or less');
        }

        if (lastName.length > 50) {
            throw new BadRequestException('Last name must be 50 characters or less');
        }

        if (password.length < 8) {
            throw new BadRequestException('Password must be at least 8 characters');
        }

        return { email, phone, username, firstName, lastName, password };
    }

    private normalizeRequired(value: string | undefined, field: string): string {
        const normalized = value?.trim();
        if (!normalized) {
            throw new BadRequestException(`${field} is required`);
        }

        return normalized;
    }

    private async hashPassword(password: string): Promise<{ hash: string; salt: string }> {
        const salt = randomBytes(PASSWORD_SALT_BYTES);
        const hash = await scryptAsync(password, salt, PASSWORD_HASH_BYTES);

        return {
            hash: hash.toString('hex'),
            salt: salt.toString('hex'),
        };
    }

    private async verifyPassword(password: string, saltHex: string, expectedHashHex: string): Promise<boolean> {
        const salt = Buffer.from(saltHex, 'hex');
        const expectedHash = Buffer.from(expectedHashHex, 'hex');
        const actualHash = await scryptAsync(password, salt, expectedHash.length);

        return actualHash.length === expectedHash.length && timingSafeEqual(actualHash, expectedHash);
    }

    private extractAuthCookie(request: AuthenticatedRequest): string | undefined {
        const cookieHeader = request.headers.cookie;
        if (!cookieHeader) {
            return undefined;
        }

        const cookieName = this.getCookieName();
        return cookieHeader
            .split(';')
            .map(cookie => cookie.trim())
            .map(cookie => {
                const separatorIndex = cookie.indexOf('=');
                if (separatorIndex < 0) {
                    return undefined;
                }

                const name = cookie.slice(0, separatorIndex);
                const value = cookie.slice(separatorIndex + 1);
                return name === cookieName ? this.decodeCookieValue(value) : undefined;
            })
            .find((value): value is string => Boolean(value));
    }

    private decodeCookieValue(value: string): string | undefined {
        try {
            return decodeURIComponent(value);
        } catch {
            return undefined;
        }
    }

    private getExpiresInSeconds(): number {
        const configured = Number(this.config.get<string>('JWT_EXPIRES_SECONDS', '604800'));
        return Number.isFinite(configured) && configured > 0 ? configured : 604800;
    }

    private toPublicUser(user: User): PublicUser {
        return {
            userId: Number(user.userId),
            email: user.email,
            phone: user.phone,
            username: user.username,
            firstName: user.firstName,
            lastName: user.lastName,
        };
    }
}
