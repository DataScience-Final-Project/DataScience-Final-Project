import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { SequelizeModule } from '@nestjs/sequelize';
import { AuthModule } from './auth/auth.module';
import { CityModule } from './entities/city/city.module';
import { HeatmapModule } from './entities/heatmap/heatmap.module';
import { PropertyModule } from './entities/property/property.module';
import { SavedSearchModule } from './entities/savedSearch/savedSearch.module';
import { UserModule } from './entities/user/user.module';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    SequelizeModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        dialect: 'postgres',
        host: config.get<string>('DB_HOST', 'localhost'),
        port: config.get<number>('DB_PORT', 5432),
        username: config.get<string>('DB_USER', 'postgres'),
        password: config.get<string>('DB_PASS', ''),
        database: config.get<string>('DB_NAME', ''),
        autoLoadModels: true,
        synchronize: false,
        logging: false,
      }),
    }),
    AuthModule,
    CityModule,
    HeatmapModule,
    PropertyModule,
    SavedSearchModule,
    UserModule,
  ],
})
export class AppModule {}
