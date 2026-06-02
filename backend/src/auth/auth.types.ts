import type { Request } from "express";

export type PublicUser = {
    userId: number;
    email: string;
    phone: string;
    username: string;
};

export type AuthenticatedRequest = Request & {
    user?: PublicUser;
};

export type JwtPayload = {
    sub: number;
    email: string;
    username: string;
    iat: number;
    exp: number;
};
