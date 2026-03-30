<<~ORIG
count = 0
def black():
  print(233)
if __name__ == '__main__'
  exit()
ORIG

<<~MODIFY
count = 0
-def black():
+def hello
+  global coount
+  global += 1
-  print(233)
+  print('hello, world!')
    
MODIFY

def modify_diff orig, text
end