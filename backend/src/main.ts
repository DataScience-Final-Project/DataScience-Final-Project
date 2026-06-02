import { NestFactory } from '@nestjs/core';
import { ConfigService } from '@nestjs/config';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  const config = app.get(ConfigService);
  const configuredOrigins = config.get<string>('FRONTEND_ORIGIN');

  app.enableCors({
    origin: configuredOrigins ? configuredOrigins.split(',').map(origin => origin.trim()) : true,
    credentials: true,
  });

  await app.listen(process.env.PORT ?? 4000);
}
bootstrap();
