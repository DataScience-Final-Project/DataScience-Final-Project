import { CanActivate, ExecutionContext, Injectable } from "@nestjs/common";
import type { AuthenticatedRequest } from "./auth.types";
import { AuthService } from "./auth.service";

@Injectable()
export class JwtCookieAuthGuard implements CanActivate {
    constructor(private readonly authService: AuthService) { }

    async canActivate(context: ExecutionContext): Promise<boolean> {
        const request = context.switchToHttp().getRequest<AuthenticatedRequest>();
        request.user = await this.authService.authenticateRequest(request);

        return true;
    }
}
