import { Injectable } from "@nestjs/common";
import axios from "axios";
import cities from '../israel_cities_names_and__geometric_data.json';

@Injectable()
export class CityService {
    constructor() { }

    async fetchAll() {
        return cities.map(city => city.name)
    }
}