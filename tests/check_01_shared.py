from shared.order_params import OrderParams
from shared.law import ScalingLaw

p = OrderParams.default()
print("dim:", p.dim, p.names)
print("schema properties:", len(p.schema()["properties"]))

law = ScalingLaw("2.0*n**2", {}, "O(n^2)", 1.0, 0.9, 3.0, True)
print("law at n=1000:", law.evaluate(1000))
print("insufficient ->", ScalingLaw.insufficient("thin data").evaluate(100))
