from bs4 import BeautifulSoup
import requests
import datetime
import os.path

filename = input("Enter path of csv file: ")
while filename[-4:] != ".csv":
    filename = input("Please enter a path to a csv file: ")
    
today = datetime.date.today().strftime('%-d/%-m/%y')

#check if file exists
if os.path.isfile(filename):
    # file exists, read headers from file
    file_read = open(filename, "r+")
    headers = file_read.readline().replace("\n","").replace("\r","").split(",")
    if headers[-1] == today:
        print "Already obtained today's data"
        exit()
    existing_file = True
else:
    # file doesn't exist, create file
    headers = ["title", "author", "publication_date", "retail_price"]
    file_read = open(filename, "w")
    existing_file = False

# add today's date to headers list
headers.append(today)
# record (new) number of rows
rows = len(headers)

# create list of books
csv_books = []

# add books from file to csv_books list
if existing_file:
    # each line in the csv file corresponds to a book
    for line in file_read:
        csv_books.append(line.replace("\n","").replace("\r","").split(","))
    # rewind file to beginning
    file_read.seek(0,0)


# keeps a list of books read from file that are temporarily unavailble on the website
unavailble_books = []
for book in csv_books:
    if book[3] == "-":
        unavailble_books.append(book)

search_term = input("Enter search term: ")
search_term = search_term.split(" ")
search_term = "+".join(search_term)

url = "https://www.bookdepository.com/search?searchTerm=" + search_term
lastPage = False
while not lastPage:
    source = requests.get(url)
    soup = BeautifulSoup(source.content, "lxml")
    books = soup.findAll("div", {"class":"item-info"})
    for book in books:
        # assume current book doesn't exist in the csv file and is available on bookdepository
        existing_book = False
        available = True

        # determine if the current book is still available on bookdepository
        if(book.parent.find("a", {"rel":"nofollow"}).string == "Try AbeBooks"):
            available = False

        # get title
        title = book.a.string.strip().replace(",", "")

        # get publication date
        try:
            pub_date = book.find("p", {"class":"published"}).text.strip().split()
            pub_date[2] = pub_date[2][-2:]
            # remove 0 padding from date
            if(pub_date[0][0]=="0"):
                pub_date[0] = pub_date[0][1]
            pub_date = "-".join(pub_date)
        except (AttributeError, IndexError):
          pub_date = "Not Provided"

        # get price
        if available:
            price_tag = book.find("div", {"class":"price-wrap"})
            prices = " ".join("".join([char if ord(char) < 128 else "" for char in price_tag.text]).replace(",", ".").split()).split()
            if len(prices) == 1: # only one price is listed; only two options
              # book is temporarily unavailble
              if prices[0] == "unavailable":
                  price = "-"
                  retail_price = "-"
              # selling price == retail price
              else:
                  price = prices[0].replace(" ","")
                  retail_price = price
            else:
                price = prices[0].replace(" ","")
                retail_price = prices[1].replace(" ","")

        # check whether current book matches an existing book from csv file
        for csv_book in csv_books:
            if csv_book[0] == title and csv_book[2] == pub_date:
                # remove book from csv_books if now unavailble on website
                if not available:
                    csv_books.remove(csv_book)
                    break
                # if retail price is given, update this field in the matched book
                elif not retail_price == "-":
                    for unavailble_book in unavailble_books:
                        if unavailble_book[0] == title and unavailble_book[2] == pub_date:
                            csv_book[3] = retail_price
                            unavailble_books.remove(unavailble_book)
                csv_book.append(price)
                existing_book = True
                break

        # cannot find match; add current book to csv_books
        if not existing_book and available:
            title = '"' + title + '"'
            try:
              author = book.p.a.string
            except AttributeError:
              author = "Not Provided"
            new_book = [title, author, pub_date, retail_price]
            for i in range(4, rows - 1):
                new_book.append("-")
            new_book.append(price)
            csv_books.append(new_book)

    try:
      next_url = soup.find("li", {"class":"next"}).a.get("href")
      url = "https://www.bookdepository.com" + next_url
    except AttributeError:
      lastPage = True

# write data to csv file
headers = ",".join(headers) + "\n"
file_read.write(headers)
for book in csv_books:
    file_read.write(",".join(book) + "\n")
file_read.close()
