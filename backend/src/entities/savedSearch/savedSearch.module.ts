import { Module } from "@nestjs/common";
import { SequelizeModule } from "@nestjs/sequelize";
import { AuthModule } from "../../auth/auth.module";
import { SavedSearch } from "./savedSearch.model";
import { SavedSearchController } from "./savedSearch.controller";
import { SavedSearchService } from "./savedSearch.service";

@Module({
    imports: [
        SequelizeModule.forFeature([SavedSearch]),
        AuthModule,
    ],
    controllers: [SavedSearchController],
    providers: [SavedSearchService],
})
export class SavedSearchModule { }
