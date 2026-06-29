import { Body, Controller, Get, Post, Req, Res, UseGuards } from "@nestjs/common";
import type { CookieOptions, Response } from "express";
import type { LoginRequest, SignupRequest } from "./auth.dto";
import type { AuthenticatedRequest } from "./auth.types";
import { AuthService } from "./auth.service";
import { JwtCookieAuthGuard } from "./jwt-cookie-auth.guard";

@Controller('auth')
export class AuthController {
    constructor(private readonly authService: AuthService) { }

    @Post('signup')
    async signup(@Body() dto: SignupRequest, @Res({ passthrough: true }) response: Response) {
        const session = await this.authService.signup(dto);
        response.cookie(this.authService.getCookieName(), session.token, this.getCookieOptions(session.maxAgeMs));

        return { user: session.user };
    }

    @Post('login')
    async login(@Body() dto: LoginRequest, @Res({ passthrough: true }) response: Response) {
        const session = await this.authService.login(dto);
        response.cookie(this.authService.getCookieName(), session.token, this.getCookieOptions(session.maxAgeMs));

        return { user: session.user };
    }

    @Post('logout')
    logout(@Res({ passthrough: true }) response: Response) {
        response.clearCookie(this.authService.getCookieName(), this.getCookieOptions());

        return { ok: true };
    }

    @UseGuards(JwtCookieAuthGuard)
    @Get('me')
    me(@Req() request: AuthenticatedRequest) {
        return { user: request.user };
    }

    private getCookieOptions(maxAge?: number): CookieOptions {
        return {
            httpOnly: true,
            sameSite: 'lax',
            secure: this.authService.useSecureCookies(),
            path: '/',
            maxAge,
        };
    }
}
