import { Injectable } from "@nestjs/common";
import cities from '../israel_cities_names_and__geometric_data.json';

@Injectable()
export class CityService {
    constructor() { }

    async fetchAll(filter: string) {
        return cities.filter(city =>
            city.name.includes(filter) || city.english_name.includes(filter))
            .map(city => city.name);
    }
}