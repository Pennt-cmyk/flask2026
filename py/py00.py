def square(y):
  print(f"{y} 的平方為 {y*y}") 


x = int(input("請輸入一個正整數："))
if (x<=0):
	print(f"您輸入的數字是{x},小於等於0")
else:
	print(f"您輸入的數字是{x},大於0")
	for i in range(1,x+1):
		square(i)