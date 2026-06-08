import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { SequelizeModule } from '@nestjs/sequelize';
import { AuthModule } from './auth/auth.module';
import { CityModule } from './entities/city/city.module';
import { GrowthClusterModule } from './entities/growthCluster/growthCluster.module';
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
      }),
    }),
    AuthModule,
    CityModule,
    GrowthClusterModule,
    SavedSearchModule,
    UserModule,
  ],
})

export class AppModule { }
