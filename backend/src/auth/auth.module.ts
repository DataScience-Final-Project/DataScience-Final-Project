import { Module } from "@nestjs/common";
import { SequelizeModule } from "@nestjs/sequelize";
import { User } from "../entities/user/user.model";
import { AuthController } from "./auth.controller";
import { AuthService } from "./auth.service";
import { JwtCookieAuthGuard } from "./jwt-cookie-auth.guard";
import { JwtService } from "./jwt.service";

@Module({
    imports: [
        SequelizeModule.forFeature([User]),
    ],
    controllers: [AuthController],
    providers: [AuthService, JwtService, JwtCookieAuthGuard],
    exports: [AuthService, JwtCookieAuthGuard],
})
export class AuthModule { }
