const CATEGORY_ORDER = [
  "produce",
  "dairy",
  "bakery",
  "meat",
  "pantry",
  "frozen",
  "beverages",
  "household",
  "other",
];

const CATEGORY_LABELS = {
  produce: "Produce",
  dairy: "Dairy",
  bakery: "Bakery",
  meat: "Meat",
  pantry: "Pantry",
  frozen: "Frozen",
  beverages: "Beverages",
  household: "Household",
  other: "Other",
};

function groupByCategory(items) {
  const groups = {};
  for (const item of items) {
    const category = item.category || "other";
    if (!groups[category]) groups[category] = [];
    groups[category].push(item);
  }
  return Object.entries(groups).sort(
    ([a], [b]) => CATEGORY_ORDER.indexOf(a) - CATEGORY_ORDER.indexOf(b)
  );
}
export default function ShoppingList({ items }) {
  if (items.length === 0) {
    return (
      <div className="shopping-list empty">
        <p>Your list is empty. Try saying "add milk".</p>
      </div>
    );
  }

  const groups = groupByCategory(items);

  return (
    <div className="shopping-list">
      <h2>Your List</h2>
      {groups.map(([category, groupItems]) => (
        <div className="category-group" key={category}>
          <h3 className="category-heading">
            {CATEGORY_LABELS[category] || category}
          </h3>
          <ul>
            {groupItems.map((item) => (
              <li key={item.id}>
                <span className="item-name">{item.name}</span>
                <span className="item-quantity">
                  {item.unit
                    ? `${item.quantity} ${item.unit}`
                    : item.quantity > 1
                    ? `× ${item.quantity}`
                    : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}