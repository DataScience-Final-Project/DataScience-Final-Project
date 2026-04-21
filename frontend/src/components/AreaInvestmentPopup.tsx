import "./AreaInvestmentPopup.css";

type AreaInvestmentPopupProps = {
  areaName: string;
  growthPercent: number;
  suggestedAreas: string[];
};

const AreaInvestmentPopup = ({
  areaName,
  growthPercent,
  suggestedAreas,
}: AreaInvestmentPopupProps) => {
  return (
    <div className="area-popup">
      <h3 className="area-popup__title">{areaName}</h3>
      <p className="area-popup__growth">
        Price growth: <strong>{growthPercent.toFixed(1)}%</strong>
      </p>
      <p className="area-popup__subtitle">Suggested areas to invest:</p>
      <ul className="area-popup__list">
        {suggestedAreas.map((area) => (
          <li key={area}>{area}</li>
        ))}
      </ul>
    </div>
  );
};

export type PopupMockData = {
  suggestedAreas: string[];
};

const fallbackSuggestions = ["Main center", "High-demand streets", "Near transit hubs"];

export const popupMockDataByAreaId: Record<number, PopupMockData> = {
  1: {
    suggestedAreas: ["Rothschild Blvd", "Lev Ha'Ir", "Neve Tzedek"],
  },
  2: {
    suggestedAreas: ["Bursa District", "Ramat Amidar", "Marom Nave"],
  },
  3: {
    suggestedAreas: ["Ajami", "Old Jaffa", "Noga"],
  },
  4: {
    suggestedAreas: ["Tel Baruch", "Ramat Aviv", "Neot Afeka"],
  },
};

export const getSuggestedAreasById = (areaId?: number) => {
  if (!areaId) return fallbackSuggestions;
  return popupMockDataByAreaId[areaId]?.suggestedAreas ?? fallbackSuggestions;
};

export default AreaInvestmentPopup;
