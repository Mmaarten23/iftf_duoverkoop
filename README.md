# iftf_duoverkoop
## Definitions
This is a web application designed for the yearly IF theater festival in Leuven.
The application allows admins to create 
- Associations (Theater groups that organize one or more Performances)
- Performances (A single performance of a play on a specified date by an Association)
and allows sellers to create
- Purchases    (The combination of two Performances on a single ticket)


The app is only a management tool for keeping track of how many tickets are still available for each performance.

## Running the app
### Prerequisites
- Git (https://git-scm.com/downloads)
- Pip (https://pypi.org/project/pip/)
### Getting started
1. Clone the repository from a terminal using the command `git clone https://github.com/Mmaarten23/iftf_duoverkoop.git`
1. Change your working directory to the newly cloned folder
1. Install the dependencies by running `pip install -r requirements.txt` in the terminal
1. Run the command `python manage.py runserver`

This will start the web app. You can now access the app at http://localhost:8000/ . This will load an empty page since no Associations/Performances have been created yet.
If you want to test the app with some sample data, browse to http://localhost:8000/--DEBUG--/load_db This will load 2 Associations: Wina and Politika. 
Each having some sample Performances. If you wish to add your own Associations/Performances, check the Adminstrative section below.

## Using the app
### The order page
At http://localhost:8000/order , the order screen is located. 
This screen allows a seller to fill in an ordering form consisting of the first and last name of the buyer and the two Performances they would like to combine.
Above the ordering form, an overview of all the associations and their performances can be found with the amount of tickets that are left for each Performance.

### The purchase history page
http://localhost:8000/purchase_history/ houses the purchase history for all clients. This can be used to debug or to verify that a certain purchase has gone through.


## Constraints
The current constraints on the order system are as follows (these may be subject to change depending on the IFTF needs)
1. A single person can make as many purchases as they want.
1. A purchase must contain exactly 2 performances.
1. A purchase must be for 2 separate performances.
1. A purchase for 2 performances of the same association must have those performances on different dates/times.
1. A purchase cannot be made for a performance that has sold out their available tickets

## Administrative
If you are not just checking out this app in a demo scenario but actually want to use this app, you will need to be able to create and modify data within the app.

### Logging in to the admin panel
To access the data, you will need access to the admin panel. 
1. Go to http://localhost:8000/admin/ 
1. login with username: `admin`, password: `admin` (change these if you are planning to use this app in production)

### Creating data
#### Creating Associations
The first thing you will want to do is create an Association. 
On the admin panel, click on the Associations collection, then click on `add`.
The properties for a Performance are as follows:
- `Name`: The name of the Association. Should be a short but readable identifier.
- `Image`: A square image representing the Association. A logo/shield/...

#### Creating Performances
Once there are some Associations in the system, Performances can be created. 
On the admin panel, click on the Performances collection, then click on `add`. The properties for a Performance are as follows:
- `Key`: A unique identifier for the performance. Suggested format: `AssociationDayMonth` (ex. `Wina3112` A performance by Wina on december 31st)
- `Date`: The date and time of the start of the performance. 
- `Association`: One of the previously made Associations.
- `Name`: The name of the Performance. A human readable name, can be the official name of the Performance or can be used to differentiate different versions of the Performance.
- `Price`: The price field is currently not used since the application is not handeling any price calculations but in case the different Performances would have different prices, this field may be used to indicate this price difference. Future extensions of the program may put this field to use. (must be a non-negative number) 
- `Maximum Tickets`: The maximum amount of tickets that are allowed to be sold for this Performance.

#### Creating Purchases
While it is strongly advised to use the order page for creating new purchases, it is possible to create purchases through the admin panel too.
On the admin panel, click on the Purchases collection, then click on `add`. The properties for a Purchase are as follows:
- `Date`: The date and time of the purchase. This is preferably set to `now` but can be altered if needed.
- `Name`: The full name of the customer in the format "Firstname Lastname" 
- `Ticket1`: One of the previously made Performances. This must be set to the exact key of the performance (ex. `Wina3112`).
- `Ticket2`: One of the previously made Performances. This must be set to the exact key of the performance (ex. `Wina3112`).

### Modifying data
If modifications are required, select the collection for the type of object you want to modify.
Then select the object you want to modify. For Associations and Performances, the objects will be identifyable by their name and key respectively. 
Purchases are identified by an id. These ids are also shown on the purchase history page which makes it easier to lookup a specific purchase id.

### Deleting data
Deleting objects is possible from the admin panel by selecting the checkbox next to the objects in their collection, selecting the `delete` action at the top of the page and clicking `execute`.
Please note that the database has a policy in place to avoid having broken references. Therfore, please make sure the following constraints are met:
- Removing a Purchase is always possible
- Removing a Performance is only possible if no Purchases have their Ticket1 or Ticket2 set to the key of that Performance
- Removing an Association is only possible if none of the Performances are set to that Association
