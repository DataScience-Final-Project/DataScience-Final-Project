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
  const isTwoColumnList = suggestedAreas.length > 6;

  return (
    <div className="area-popup" aria-label={`Investment details for ${areaName}`}>
      {/* <h3 className="area-popup__title">{areaName}</h3> */}
      <p className="area-popup__growth">
        Price growth: <strong>{growthPercent.toFixed(1)}%</strong>
      </p>
      
      {/* נציג את הרשימה רק אם באמת יש ערים להציג */}
      {suggestedAreas && suggestedAreas.length > 0 && (
        <>
          <p className="area-popup__subtitle">Cities in area:</p>
          <ul className={`area-popup__list ${isTwoColumnList ? "area-popup__list--two-columns" : ""}`}>
            {suggestedAreas.map((area, index) => (
              <li key={`${area}-${index}`}>{area}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
};

export default AreaInvestmentPopup;