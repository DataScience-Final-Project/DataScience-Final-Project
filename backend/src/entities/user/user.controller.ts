import { Controller, Get, Req, UseGuards } from "@nestjs/common";
import type { AuthenticatedRequest } from "../../auth/auth.types";
import { JwtCookieAuthGuard } from "../../auth/jwt-cookie-auth.guard";

@Controller('users')
export class UserController {
    @UseGuards(JwtCookieAuthGuard)
    @Get('me')
    me(@Req() request: AuthenticatedRequest) {
        return { user: request.user };
    }
}
