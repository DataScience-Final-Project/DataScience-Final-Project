import { Body, Controller, Delete, Get, Param, Post, Req, UseGuards } from "@nestjs/common";
import type { AuthenticatedRequest } from "../../auth/auth.types";
import { JwtCookieAuthGuard } from "../../auth/jwt-cookie-auth.guard";
import type { CreateSavedSearchRequest } from "./savedSearch.dto";
import { SavedSearchService } from "./savedSearch.service";

@Controller('saved-searches')
@UseGuards(JwtCookieAuthGuard)
export class SavedSearchController {
    constructor(private readonly service: SavedSearchService) { }

    @Get('')
    list(@Req() request: AuthenticatedRequest) {
        return this.service.list(request.user!.userId);
    }

    @Post('')
    create(@Req() request: AuthenticatedRequest, @Body() dto: CreateSavedSearchRequest) {
        return this.service.create(request.user!.userId, dto);
    }

    @Delete(':id')
    async remove(@Req() request: AuthenticatedRequest, @Param('id') id: string) {
        await this.service.remove(request.user!.userId, id);
        return { ok: true };
    }
}
